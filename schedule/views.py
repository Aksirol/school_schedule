from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated

from .models import (Teacher, AcademicYear, SchoolClass, Subject, Room,
                     TimeSlot, Curriculum, TeacherAvailability)
from .serializers import (TeacherSerializer, AcademicYearSerializer, SchoolClassSerializer,
                          SubjectSerializer, RoomSerializer, TimeSlotSerializer,
                          CurriculumSerializer, TeacherAvailabilitySerializer)
from .permissions import IsAdminUserRole, IsDeputyOrAdmin, IsTeacher, IsPublicReadOnly

from rest_framework.views import APIView
from rest_framework.response import Response
from celery.result import AsyncResult
from .tasks import run_schedule_generation

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