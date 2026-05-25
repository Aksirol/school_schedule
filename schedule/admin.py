from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (User, Teacher, AcademicYear, SchoolClass, Subject, Room,
                     TimeSlot, Curriculum, TeacherAvailability, Schedule, ScheduleChange)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Додаткова інформація', {'fields': ('role', 'teacher_profile')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'email', 'phone')
    search_fields = ('last_name', 'first_name')

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_number', 'academic_year')
    list_filter = ('academic_year', 'grade_number')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'name', 'capacity', 'room_type')
    list_filter = ('room_type',)

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'lesson_number', 'start_time', 'end_time')
    list_filter = ('day_of_week',)
    ordering = ('day_of_week', 'lesson_number')

@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ('school_class', 'subject', 'teacher', 'hours_per_week', 'academic_year')
    list_filter = ('academic_year', 'school_class')

@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'time_slot', 'status')
    list_filter = ('status', 'teacher')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('curriculum', 'room', 'time_slot', 'is_published')
    list_filter = ('is_published', 'time_slot__day_of_week', 'room')

@admin.register(ScheduleChange)
class ScheduleChangeAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'change_date', 'reason', 'changed_by')