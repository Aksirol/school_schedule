from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import (Teacher, AcademicYear, SchoolClass, Subject, Room,
                     TimeSlot, Curriculum, TeacherAvailability)


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


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = '__all__'


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'


class SchoolClassSerializer(serializers.ModelSerializer):
    # Додаємо назву року для зручності читання
    academic_year_name = serializers.ReadOnlyField(source='academic_year.name')

    class Meta:
        model = SchoolClass
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class TimeSlotSerializer(serializers.ModelSerializer):
    day_name = serializers.ReadOnlyField(source='get_day_of_week_display')

    class Meta:
        model = TimeSlot
        fields = '__all__'


class CurriculumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curriculum
        fields = '__all__'

    def validate(self, data):
        """Перевірка унікальності в рамках навчального року"""
        school_class = data.get('school_class')
        subject = data.get('subject')
        academic_year = data.get('academic_year')

        # Якщо це створення нового запису
        if not self.instance:
            if Curriculum.objects.filter(school_class=school_class, subject=subject,
                                         academic_year=academic_year).exists():
                raise serializers.ValidationError(
                    "Цей предмет вже призначено для даного класу в цьому навчальному році.")
        return data


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherAvailability
        fields = '__all__'