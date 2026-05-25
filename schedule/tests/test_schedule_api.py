from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from datetime import date, time
from django.utils import timezone
from schedule.models import User, AcademicYear, SchoolClass, Subject, Teacher, TimeSlot, Room, Curriculum, Schedule, \
    ScheduleChange


class ScheduleAPITests(APITestCase):
    def setUp(self):
        # 1. Користувачі
        self.deputy = User.objects.create_user(username='deputy', password='123', role='DEPUTY')
        self.student = User.objects.create_user(username='student', password='123', role='STUDENT')

        # 2. Базові дані
        self.year = AcademicYear.objects.create(name='2023-2024', start_date=date(2023, 9, 1),
                                                end_date=date(2024, 5, 31))
        self.school_class = SchoolClass.objects.create(name='10-А', grade_number=10, academic_year=self.year)
        self.subject = Subject.objects.create(name='Математика')

        # Використовуємо унікальний email, як ми з'ясували в попередніх тестах
        self.teacher_profile = Teacher.objects.create(first_name='Іван', last_name='Математик',
                                                      email='math_phase6@school.com')

        self.room_101 = Room.objects.create(name='Каб 101', room_number='101', capacity=30, room_type='Звичайний')
        self.room_201 = Room.objects.create(name='Каб 201', room_number='201', capacity=30, room_type='Звичайний')

        self.slot_1 = TimeSlot.objects.create(day_of_week='MON', lesson_number=1, start_time=time(8, 30),
                                              end_time=time(9, 15))
        self.slot_2 = TimeSlot.objects.create(day_of_week='MON', lesson_number=2, start_time=time(9, 25),
                                              end_time=time(10, 10))

        # Навчальний план
        self.curr = Curriculum.objects.create(school_class=self.school_class, subject=self.subject,
                                              teacher=self.teacher_profile, hours_per_week=2, academic_year=self.year)

    def test_publish_all(self):
        """Тест Z3: Публікація всього розкладу для навчального року"""
        # Створюємо 2 неопубліковані уроки
        Schedule.objects.create(curriculum=self.curr, room=self.room_101, time_slot=self.slot_1, is_published=False)
        Schedule.objects.create(curriculum=self.curr, room=self.room_101, time_slot=self.slot_2, is_published=False)

        url = reverse('schedule-publish-all')  # DRF Router автоматично створює таке ім'я
        data = {'academic_year_id': self.year.id}

        self.client.force_authenticate(user=self.deputy)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['published_count'], 2)

        # Перевіряємо в базі даних, чи змінився статус
        schedules = Schedule.objects.all()
        for sched in schedules:
            self.assertTrue(sched.is_published)
            self.assertIsNotNone(sched.published_at)

    def test_manual_move_success_and_history(self):
        """Тест Z2: Успішне перенесення уроку та перевірка Журналу змін"""
        schedule = Schedule.objects.create(
            curriculum=self.curr, room=self.room_101, time_slot=self.slot_1,
            is_published=True, published_at=timezone.now()
        )

        url = reverse('schedule-manual-move', kwargs={'pk': schedule.id})
        data = {
            'new_time_slot_id': self.slot_2.id,
            'new_room_id': self.room_201.id,
            'reason': 'Заміна кабінету через ремонт'
        }

        self.client.force_authenticate(user=self.deputy)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Перевіряємо, чи урок дійсно перемістився
        schedule.refresh_from_db()
        self.assertEqual(schedule.time_slot, self.slot_2)
        self.assertEqual(schedule.room, self.room_201)

        # Перевіряємо, чи створено запис в ScheduleChange
        changes = ScheduleChange.objects.filter(schedule=schedule)
        self.assertEqual(changes.count(), 1)
        self.assertEqual(changes[0].reason, 'Заміна кабінету через ремонт')
        self.assertEqual(changes[0].changed_by, self.deputy)

    def test_manual_move_conflict(self):
        """Тест Z2: Блокування перенесення при конфлікті (вчитель вже зайнятий)"""
        # Урок 1 (для 10-А)
        schedule_1 = Schedule.objects.create(curriculum=self.curr, room=self.room_101, time_slot=self.slot_1,
                                             is_published=True)

        # Урок 2 (для іншого класу, але того ж вчителя)
        class_11b = SchoolClass.objects.create(name='11-Б', grade_number=11, academic_year=self.year)
        curr_11b = Curriculum.objects.create(school_class=class_11b, subject=self.subject, teacher=self.teacher_profile,
                                             hours_per_week=1, academic_year=self.year)
        schedule_2 = Schedule.objects.create(curriculum=curr_11b, room=self.room_201, time_slot=self.slot_2,
                                             is_published=True)

        # Пробуємо перенести Урок 1 на час Уроку 2
        url = reverse('schedule-manual-move', kwargs={'pk': schedule_1.id})
        data = {
            'new_time_slot_id': self.slot_2.id,
            'new_room_id': self.room_101.id
        }

        self.client.force_authenticate(user=self.deputy)
        response = self.client.post(url, data)

        # Бекенд має відхилити таку зміну з помилкою 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Конфлікт', str(response.data))

    def test_schedule_permissions(self):
        """Тест: Ролі доступу до розкладу"""
        url_list = reverse('schedule-list')

        # Студент може читати сітку розкладу
        self.client.force_authenticate(user=self.student)
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Студент НЕ може масово публікувати розклад
        url_publish = reverse('schedule-publish-all')
        response = self.client.post(url_publish, {'academic_year_id': self.year.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)