from django.test import TestCase
from datetime import date, time
from schedule.models import User, AcademicYear, SchoolClass, Subject, Teacher, TimeSlot, Room, Curriculum, \
    TeacherAvailability, Schedule
from schedule.engine import generate_schedule_engine


class EngineTests(TestCase):
    def setUp(self):
        # 1. Базові дані
        self.year = AcademicYear.objects.create(name='2023-2024', start_date=date(2023, 9, 1),
                                                end_date=date(2024, 5, 31))

        self.class_10a = SchoolClass.objects.create(name='10-А', grade_number=10, academic_year=self.year)
        self.class_11b = SchoolClass.objects.create(name='11-Б', grade_number=11, academic_year=self.year)

        self.math = Subject.objects.create(name='Математика')
        self.physics = Subject.objects.create(name='Фізика')

        self.teacher_math = Teacher.objects.create(first_name='Іван', last_name='Математик', email='math@school.com')
        self.teacher_phys = Teacher.objects.create(first_name='Петро', last_name='Фізик', email='phys@school.com')

        self.room_101 = Room.objects.create(name='Каб 101', room_number='101', capacity=30, room_type='Звичайний')
        self.room_201 = Room.objects.create(name='Каб 201', room_number='201', capacity=30, room_type='Звичайний')

        # Створюємо 3 часові слоти (Понеділок 1, 2, 3 уроки)
        self.slot_1 = TimeSlot.objects.create(day_of_week='MON', lesson_number=1, start_time=time(8, 30),
                                              end_time=time(9, 15))
        self.slot_2 = TimeSlot.objects.create(day_of_week='MON', lesson_number=2, start_time=time(9, 25),
                                              end_time=time(10, 10))
        self.slot_3 = TimeSlot.objects.create(day_of_week='MON', lesson_number=3, start_time=time(10, 30),
                                              end_time=time(11, 15))

    def test_successful_generation(self):
        """Тест: Успішна генерація без конфліктів"""
        # Створюємо навчальний план (2 години математики для 10-А)
        Curriculum.objects.create(school_class=self.class_10a, subject=self.math, teacher=self.teacher_math,
                                  hours_per_week=2, academic_year=self.year)

        result = generate_schedule_engine(self.year.id)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['lessons_scheduled'], 2)
        self.assertEqual(len(result['unresolved_conflicts']), 0)

        # Перевіряємо базу
        schedules = Schedule.objects.all()
        self.assertEqual(schedules.count(), 2)
        # Уроки мають бути на різних слотах
        self.assertNotEqual(schedules[0].time_slot, schedules[1].time_slot)

    def test_teacher_conflict(self):
        """Тест: Конфлікт вчителя (один вчитель не може вести 2 уроки одночасно)"""
        # Тільки ОДИН часовий слот у школі
        TimeSlot.objects.exclude(id=self.slot_1.id).delete()

        # Один вчитель веде математику у ДВОХ класах
        Curriculum.objects.create(school_class=self.class_10a, subject=self.math, teacher=self.teacher_math,
                                  hours_per_week=1, academic_year=self.year)
        Curriculum.objects.create(school_class=self.class_11b, subject=self.math, teacher=self.teacher_math,
                                  hours_per_week=1, academic_year=self.year)

        result = generate_schedule_engine(self.year.id)

        # Має бути частковий успіх (лише 1 урок поставлено)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['lessons_scheduled'], 1)
        self.assertEqual(len(result['unresolved_conflicts']), 1)
        self.assertIn("Не знайдено слот:", result['unresolved_conflicts'][0])

    def test_teacher_availability(self):
        """Тест: Врахування недоступності вчителя (TeacherAvailability)"""
        # Створюємо план: 1 година математики
        curr = Curriculum.objects.create(school_class=self.class_10a, subject=self.math, teacher=self.teacher_math,
                                         hours_per_week=1, academic_year=self.year)

        # Вчитель недоступний на 1 і 2 уроках
        TeacherAvailability.objects.create(teacher=self.teacher_math, time_slot=self.slot_1, status='UNAVAILABLE')
        TeacherAvailability.objects.create(teacher=self.teacher_math, time_slot=self.slot_2, status='UNAVAILABLE')

        generate_schedule_engine(self.year.id)

        # Урок має бути поставлений на 3-й слот!
        schedule = Schedule.objects.get(curriculum=curr)
        self.assertEqual(schedule.time_slot, self.slot_3)