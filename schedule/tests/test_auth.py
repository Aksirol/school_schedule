from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from schedule.models import User
import jwt  # Для декодування токена


class AuthTests(APITestCase):
    def setUp(self):
        # Цей метод запускається перед кожним тестом
        self.user = User.objects.create_user(
            username='teacher_john',
            password='securepassword123',
            role='TEACHER'
        )
        self.token_url = reverse('token_obtain_pair')  # URL з schedule/urls.py

    def test_login_success(self):
        """Перевірка успішного входу та отримання токенів"""
        data = {
            'username': 'teacher_john',
            'password': 'securepassword123'
        }
        response = self.client.post(self.token_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_invalid_credentials(self):
        """Перевірка входу з неправильним паролем"""
        data = {
            'username': 'teacher_john',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.token_url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_custom_claims(self):
        """Перевірка наявності кастомних полів (роль, юзернейм) у JWT токені"""
        data = {'username': 'teacher_john', 'password': 'securepassword123'}
        response = self.client.post(self.token_url, data)

        access_token = response.data['access']

        # Декодуємо токен (без перевірки підпису, просто щоб перевірити payload)
        decoded_payload = jwt.decode(access_token, options={"verify_signature": False})

        self.assertEqual(decoded_payload['role'], 'TEACHER')
        self.assertEqual(decoded_payload['username'], 'teacher_john')