from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Додаємо кастомні поля (claims)
        token['role'] = user.role
        token['username'] = user.username

        # Якщо це вчитель, додаємо його ID для майбутніх запитів
        if user.role == 'TEACHER' and user.teacher_profile:
            token['teacher_id'] = user.teacher_profile.id

        return token