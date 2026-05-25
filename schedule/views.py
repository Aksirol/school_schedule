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

import openpyxl
from django.http import HttpResponse
from django.db.models import Sum
from rest_framework.views import APIView
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


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
        """Z2: Ручне переміщення уроку (Drag & Drop) з повною перевіркою конфліктів"""
        schedule = self.get_object()
        new_time_slot_id = request.data.get('new_time_slot_id')
        new_room_id = request.data.get('new_room_id')
        reason = request.data.get('reason', 'Ручне перенесення розкладу')

        # ПОВНА ПЕРЕВІРКА КОНФЛІКТІВ
        teacher_conflict = Schedule.objects.filter(curriculum__teacher=schedule.curriculum.teacher,
                                                   time_slot_id=new_time_slot_id).exclude(id=schedule.id).exists()
        class_conflict = Schedule.objects.filter(curriculum__school_class=schedule.curriculum.school_class,
                                                 time_slot_id=new_time_slot_id).exclude(id=schedule.id).exists()
        room_conflict = Schedule.objects.filter(room_id=new_room_id, time_slot_id=new_time_slot_id).exclude(
            id=schedule.id).exists()

        if teacher_conflict:
            return Response({"error": "Конфлікт: Вчитель вже має урок у цей час"}, status=status.HTTP_400_BAD_REQUEST)
        if class_conflict:
            return Response({"error": "Конфлікт: Клас вже має урок у цей час"}, status=status.HTTP_400_BAD_REQUEST)
        if room_conflict:
            return Response({"error": "Конфлікт: Кабінет вже зайнятий у цей час"}, status=status.HTTP_400_BAD_REQUEST)

        # Фіксація в журналі змін
        if schedule.is_published:
            ScheduleChange.objects.create(
                schedule=schedule,
                new_room_id=new_room_id,
                new_time_slot_id=new_time_slot_id,
                change_date=timezone.now().date(),
                reason=reason,
                changed_by=request.user
            )

        schedule.time_slot_id = new_time_slot_id
        if new_room_id:
            schedule.room_id = new_room_id
        schedule.save()  # Тепер це викличе clean(), що є додатковою страховкою

        return Response({'status': 'moved_successfully'})

    @action(detail=False, methods=['get'], url_path='export/xlsx')
    def export_xlsx(self, request):
        """Експорт розкладу у формат Excel"""
        class_id = request.query_params.get('class_id')
        queryset = self.filter_queryset(self.get_queryset().filter(is_published=True))

        if class_id:
            queryset = queryset.filter(curriculum__school_class_id=class_id)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Розклад"

        # Заголовки колонок
        headers = ['День', 'Урок', 'Клас', 'Предмет', 'Вчитель', 'Кабінет']
        ws.append(headers)

        for item in queryset.order_by('time_slot__day_of_week', 'time_slot__lesson_number'):
            ws.append([
                item.time_slot.get_day_of_week_display(),
                item.time_slot.lesson_number,
                item.curriculum.school_class.name,
                item.curriculum.subject.name,
                f"{item.curriculum.teacher.last_name} {item.curriculum.teacher.first_name}",
                item.room.room_number
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="schedule.xlsx"'
        wb.save(response)
        return response

    @action(detail=False, methods=['get'], url_path='export/pdf')
    def export_pdf(self, request):
        """Експорт розкладу у формат PDF з підтримкою кирилиці"""
        class_id = request.query_params.get('class_id')
        queryset = self.filter_queryset(self.get_queryset().filter(is_published=True))

        if class_id:
            queryset = queryset.filter(curriculum__school_class_id=class_id)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="schedule.pdf"'

        # Реєстрація шрифту DejaVu для правильного відображення української мови
        try:
            pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            font_name = 'DejaVu'
        except Exception as e:
            font_name = 'Helvetica'  # Резервний варіант

        doc = SimpleDocTemplate(response, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        styleH = styles['Heading1']
        styleH.fontName = font_name

        elements.append(Paragraph("Зведений розклад занять", styleH))

        # Формування даних таблиці
        data = [['День', 'Урок', 'Клас', 'Предмет', 'Вчитель', 'Каб.']]
        for item in queryset.order_by('time_slot__day_of_week', 'time_slot__lesson_number'):
            data.append([
                item.time_slot.get_day_of_week_display(),
                str(item.time_slot.lesson_number),
                item.curriculum.school_class.name,
                item.curriculum.subject.name,
                item.curriculum.teacher.last_name,
                item.room.room_number
            ])

        # Стилізація таблиці
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),  # Синій заголовок
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
        ]))

        elements.append(table)
        doc.build(elements)

        return response


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


class TeacherLoadReportView(APIView):
    permission_classes = [IsDeputyOrAdmin]

    def get(self, request):
        """Z4: Звіт навантаження вчителів (порівняння з нормативом 18 годин)"""
        # Агрегуємо години по кожному вчителю з навчального плану
        teachers = Teacher.objects.annotate(
            total_hours=Sum('curriculum__hours_per_week')
        )

        report_data = []
        for teacher in teachers:
            hours = teacher.total_hours or 0
            norm = 18  # Стандартна ставка вчителя
            report_data.append({
                'teacher_id': teacher.id,
                'name': f"{teacher.last_name} {teacher.first_name}",
                'total_hours': hours,
                'norm_hours': norm,
                'difference': hours - norm  # Позитивне число = перепрацювання, негативне = недобір
            })

        return Response(report_data)