from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class Teacher(models.Model):
    first_name = models.CharField(max_length=50, verbose_name="Ім'я")
    last_name = models.CharField(max_length=50, verbose_name="Прізвище")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', _('Адміністратор')
        DEPUTY = 'DEPUTY', _('Заступник директора з НВР')
        TEACHER = 'TEACHER', _('Вчитель')
        STUDENT = 'STUDENT', _('Учень / Батьки')

    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.STUDENT)
    teacher_profile = models.OneToOneField(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profile'
    )
    # created_at є вбудованим date_joined в AbstractUser

class AcademicYear(models.Model):
    name = models.CharField(max_length=50, verbose_name="Назва (напр. 2023-2024)")
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name

class SchoolClass(models.Model):
    name = models.CharField(max_length=10, verbose_name="Назва (напр. 10-А)")
    grade_number = models.IntegerField(verbose_name="Паралель (клас)")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='classes')

    def __str__(self):
        return f"{self.name} ({self.academic_year.name})"

class Subject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Room(models.Model):
    name = models.CharField(max_length=50, verbose_name="Назва")
    room_number = models.CharField(max_length=20, verbose_name="Номер кабінету")
    capacity = models.IntegerField(verbose_name="Місткість")
    room_type = models.CharField(max_length=50, verbose_name="Тип (напр. Комп'ютерний клас)")

    def __str__(self):
        return f"Каб. {self.room_number} - {self.name}"

class TimeSlot(models.Model):
    DAYS_OF_WEEK = [
        ('MON', 'Понеділок'), ('TUE', 'Вівторок'), ('WED', 'Середа'),
        ('THU', 'Четвер'), ('FRI', 'П\'ятниця'),
    ]
    lesson_number = models.IntegerField(verbose_name="Номер уроку")
    start_time = models.TimeField()
    end_time = models.TimeField()
    day_of_week = models.CharField(max_length=3, choices=DAYS_OF_WEEK)

    class Meta:
        unique_together = ('lesson_number', 'day_of_week')

    def __str__(self):
        return f"{self.get_day_of_week_display()}, Урок {self.lesson_number} ({self.start_time}-{self.end_time})"

class Curriculum(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    hours_per_week = models.IntegerField(verbose_name="Годин на тиждень")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.subject} - {self.school_class} ({self.teacher})"

class TeacherAvailability(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=[('AVAILABLE', 'Доступний'), ('UNAVAILABLE', 'Недоступний')])

    def __str__(self):
        return f"{self.teacher} - {self.time_slot}: {self.status}"

class Schedule(models.Model):
    curriculum = models.ForeignKey(Curriculum, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    week_number = models.IntegerField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        """Захист бази даних від дублювання (Конфлікти)"""
        # 1. Конфлікт кабінету
        if Schedule.objects.filter(room=self.room, time_slot=self.time_slot).exclude(id=self.id).exists():
            raise ValidationError("Цей кабінет вже зайнятий у цей час.")
        # 2. Конфлікт вчителя
        if Schedule.objects.filter(curriculum__teacher=self.curriculum.teacher, time_slot=self.time_slot).exclude(id=self.id).exists():
            raise ValidationError("Вчитель вже має урок у цей час.")
        # 3. Конфлікт класу
        if Schedule.objects.filter(curriculum__school_class=self.curriculum.school_class, time_slot=self.time_slot).exclude(id=self.id).exists():
            raise ValidationError("Цей клас вже має урок у цей час.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.curriculum.school_class} - {self.curriculum.subject} ({self.time_slot})"

class ScheduleChange(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='changes')
    new_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    new_time_slot = models.ForeignKey(TimeSlot, on_delete=models.SET_NULL, null=True, blank=True)
    change_date = models.DateField()
    reason = models.CharField(max_length=255)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Зміна для {self.schedule} на {self.change_date}"