from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import (TeacherViewSet, AcademicYearViewSet, SchoolClassViewSet,
                    SubjectViewSet, RoomViewSet, TimeSlotViewSet,
                    CurriculumViewSet, TeacherAvailabilityViewSet,
                    GenerateScheduleView, TeacherLoadReportView)
from .views import ScheduleViewSet, ScheduleChangeViewSet

# Реєстрація роутера
router = DefaultRouter()
router.register(r'teachers', TeacherViewSet)
router.register(r'academic-years', AcademicYearViewSet)
router.register(r'classes', SchoolClassViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'rooms', RoomViewSet)
router.register(r'timeslots', TimeSlotViewSet)
router.register(r'curriculums', CurriculumViewSet)
router.register(r'availabilities', TeacherAvailabilityViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'schedule-changes', ScheduleChangeViewSet)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


urlpatterns = [
    # Аутентифікація
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Підключення CRUD ендпоінтів
    path('', include(router.urls)),

    path('generate/<int:year_id>/', GenerateScheduleView.as_view(), name='trigger-generation'),
    path('generate/status/<str:task_id>/', GenerateScheduleView.as_view(), name='status-generation'),

    # Новий ендпоінт для звіту
    path('reports/teacher-load/', TeacherLoadReportView.as_view(), name='report-teacher-load'),
]