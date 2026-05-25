from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated

from .models import (Teacher, AcademicYear, SchoolClass, Subject, Room,
                     TimeSlot, Curriculum, TeacherAvailability)
from .serializers import (TeacherSerializer, AcademicYearSerializer, SchoolClassSerializer,
                          SubjectSerializer, RoomSerializer, TimeSlotSerializer,
                          CurriculumSerializer, TeacherAvailabilitySerializer)
from .permissions import IsAdminUserRole, IsDeputyOrAdmin, IsTeacher, IsPublicReadOnly

from rest_framework.views import APIView
from celery.result import AsyncResult
from .tasks import run_schedule_generation
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import Schedule, ScheduleChange, TimeSlot, Room
from .serializers import ScheduleReadSerializer, ScheduleWriteSerializer, ScheduleChangeSerializer


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all().select_related('curriculum__subject', 'curriculum__teacher',
                                                     'curriculum__school_class', 'room', 'time_slot')
    filter_backends = [DjangoFilterBackend]
    # Налаштовуємо фільтри для UI (по класу, вчителю, статусу публікації)
    filterset_fields = ['curriculum__school_class', 'curriculum__teacher', 'time_slot__day_of_week', 'is_published',
                        'curriculum__academic_year']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ScheduleReadSerializer
        return ScheduleWriteSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsPublicReadOnly()]
        return [IsDeputyOrAdmin()]  # Тільки заступник/адмін може змінювати розклад

    @action(detail=False, methods=['post'])
    def publish_all(self, request):
        """Z3: Публікація розкладу для навчального року"""
        year_id = request.data.get('academic_year_id')
        if not year_id:
            return Response({"error": "academic_year_id обов'язковий"}, status=status.HTTP_400_BAD_REQUEST)

        schedules = Schedule.objects.filter(curriculum__academic_year_id=year_id, is_published=False)
        count = schedules.update(is_published=True, published_at=timezone.now())

        return Response({'status': 'success', 'published_count': count})

    @action(detail=True, methods=['post'])
    def manual_move(self, request, pk=None):
        """Z2: Ручне переміщення уроку (Drag & Drop) з фіксацією змін"""
        schedule = self.get_object()
        new_time_slot_id = request.data.get('new_time_slot_id')
        new_room_id = request.data.get('new_room_id')
        reason = request.data.get('reason', 'Ручне перенесення розкладу')

        # 1. Перевірка конфліктів (Спрощена версія для прикладу)
        if Schedule.objects.filter(curriculum__teacher=schedule.curriculum.teacher,
                                   time_slot_id=new_time_slot_id).exclude(id=schedule.id).exists():
            return Response({"error": "Конфлікт: Вчитель вже має урок у цей час"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Фіксація в журналі змін (ScheduleChanges), якщо розклад вже опубліковано
        if schedule.is_published:
            ScheduleChange.objects.create(
                schedule=schedule,
                new_room_id=new_room_id,
                new_time_slot_id=new_time_slot_id,
                change_date=timezone.now().date(),
                reason=reason,
                changed_by=request.user
            )

        # 3. Оновлення самого запису
        schedule.time_slot_id = new_time_slot_id
        if new_room_id:
            schedule.room_id = new_room_id
        schedule.save()

        return Response({'status': 'moved_successfully'})


class ScheduleChangeViewSet(viewsets.ReadOnlyModelViewSet):
    """API для перегляду журналу змін (тільки для читання)"""
    queryset = ScheduleChange.objects.all().order_by('-change_date')
    serializer_class = ScheduleChangeSerializer
    permission_classes = [IsDeputyOrAdmin]

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsPublicReadOnly]  # Адміни/Заступники пишуть, всі читають


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAdminUserRole]  # Тільки адмін керує роками


class SchoolClassViewSet(viewsets.ModelViewSet):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassSerializer
    permission_classes = [IsPublicReadOnly]


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsPublicReadOnly]


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsPublicReadOnly]


class TimeSlotViewSet(viewsets.ModelViewSet):
    queryset = TimeSlot.objects.all().order_by('day_of_week', 'lesson_number')
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAdminUserRole]  # Тільки адмін налаштовує слоти дзвінків


class CurriculumViewSet(viewsets.ModelViewSet):
    queryset = Curriculum.objects.all()
    serializer_class = CurriculumSerializer
    permission_classes = [IsDeputyOrAdmin]  # Заступник або Адмін складають план


class TeacherAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = TeacherAvailability.objects.all()
    serializer_class = TeacherAvailabilitySerializer

    def get_permissions(self):
        """Вчитель може створювати свої обмеження, Адмін/Заступник бачать всі"""
        if self.request.method in permissions.SAFE_METHODS:
            return [IsAuthenticated()]  # або кастомний пермішн
        return [IsTeacher()]  # Змінювати можуть лише вчителі


class GenerateScheduleView(APIView):
    permission_classes = [IsDeputyOrAdmin]

    def post(self, request, year_id):
        """Запуск фонової генерації"""
        task = run_schedule_generation.delay(year_id)
        return Response({'task_id': task.id, 'status': 'PROCESSING'}, status=202)

    def get(self, request, task_id):
        """Перевірка статусу виконання"""
        task_result = AsyncResult(task_id)

        response_data = {
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None
        }
        return Response(response_data)