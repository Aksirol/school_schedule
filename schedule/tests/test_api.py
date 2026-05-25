from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from datetime import date, time
from schedule.models import User, AcademicYear, SchoolClass, Subject, Teacher, TimeSlot, Curriculum


class APITests(APITestCase):
    def setUp(self):
        # 1. Створюємо користувачів з різними ролями
        self.admin = User.objects.create_user(username='admin', password='123', role='ADMIN')
        self.deputy = User.objects.create_user(username='deputy', password='123', role='DEPUTY')
        self.teacher_user = User.objects.create_user(username='teacher', password='123', role='TEACHER')
        self.student = User.objects.create_user(username='student', password='123', role='STUDENT')

        # 2. Базові дані для тестів
        self.year = AcademicYear.objects.create(name='2023-2024', start_date=date(2023, 9, 1),
                                                end_date=date(2024, 5, 31))
        self.school_class = SchoolClass.objects.create(name='10-А', grade_number=10, academic_year=self.year)
        self.subject = Subject.objects.create(name='Математика')
        self.teacher_profile = Teacher.objects.create(first_name='Іван', last_name='Петров', email='ivan@test.com')

    def test_academic_year_permissions(self):
        """Тест: AcademicYear доступний лише для ADMIN"""
        url = reverse('academicyear-list')  # генерується роутером (назва моделі в нижньому регістрі + '-list')

        # Запит від студента (має бути заборонено)
        self.client.force_authenticate(user=self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Запит від адміна (має бути дозволено)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_read_only_permissions(self):
        """Тест: IsPublicReadOnly для вчителів (TeacherViewSet)"""
        url = reverse('teacher-list')

        # Студент може читати (GET)
        self.client.force_authenticate(user=self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Студент НЕ може створювати (POST)
        data = {'first_name': 'Олег', 'last_name': 'Сидоров', 'email': 'oleg@test.com'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Адмін може створювати (POST)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_curriculum_creation_permissions(self):
        """Тест: Curriculum можуть створювати лише ADMIN та DEPUTY"""
        url = reverse('curriculum-list')
        data = {
            'school_class': self.school_class.id,
            'subject': self.subject.id,
            'teacher': self.teacher_profile.id,
            'hours_per_week': 5,
            'academic_year': self.year.id
        }

        # Вчитель пробує створити план
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Заступник пробує створити план
        self.client.force_authenticate(user=self.deputy)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_curriculum_validation(self):
        """Тест: Валідація унікальності предмета для класу в навчальному році"""
        url = reverse('curriculum-list')
        data = {
            'school_class': self.school_class.id,
            'subject': self.subject.id,
            'teacher': self.teacher_profile.id,
            'hours_per_week': 5,
            'academic_year': self.year.id
        }

        self.client.force_authenticate(user=self.admin)

        # Перше створення (успішно)
        response1 = self.client.post(url, data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Спроба додати той самий предмет для того ж класу в тому ж році
        response2 = self.client.post(url, data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Цей предмет вже призначено", str(response2.data))