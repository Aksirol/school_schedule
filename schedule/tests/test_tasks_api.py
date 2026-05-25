from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch
from datetime import date
from schedule.models import User, AcademicYear


class CeleryAPITests(APITestCase):
    def setUp(self):
        self.deputy = User.objects.create_user(username='deputy', password='123', role='DEPUTY')
        self.student = User.objects.create_user(username='student', password='123', role='STUDENT')
        self.year = AcademicYear.objects.create(name='2023-2024', start_date=date(2023, 9, 1),
                                                end_date=date(2024, 5, 31))

    @patch('schedule.views.run_schedule_generation.delay')
    def test_trigger_generation_endpoint(self, mock_delay):
        """Тест: Ендпоінт запуску генерації відповідає 202 і повертає task_id"""
        # Мокаємо Celery task, щоб він не виконувався насправді, а просто повернув ID
        mock_task = mock_delay.return_value
        mock_task.id = "fake-task-uuid"

        url = reverse('trigger-generation', kwargs={'year_id': self.year.id})

        # Студент не має права
        self.client.force_authenticate(user=self.student)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Заступник має право
        self.client.force_authenticate(user=self.deputy)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['task_id'], "fake-task-uuid")
        self.assertEqual(response.data['status'], "PROCESSING")

        # Перевіряємо, чи викликався celery task
        mock_delay.assert_called_once_with(self.year.id)

    @patch('schedule.views.AsyncResult')
    def test_status_generation_endpoint(self, mock_async_result):
        """Тест: Ендпоінт статусу повертає стан задачі"""
        # Мокаємо об'єкт AsyncResult з Celery
        mock_instance = mock_async_result.return_value
        mock_instance.status = "SUCCESS"
        mock_instance.ready.return_value = True
        mock_instance.result = {"status": "success", "lessons_scheduled": 50}

        url = reverse('status-generation', kwargs={'task_id': 'fake-task-uuid'})

        self.client.force_authenticate(user=self.deputy)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], "SUCCESS")
        self.assertEqual(response.data['result']['lessons_scheduled'], 50)