from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import (TeacherViewSet, AcademicYearViewSet, SchoolClassViewSet,
                    SubjectViewSet, RoomViewSet, TimeSlotViewSet,
                    CurriculumViewSet, TeacherAvailabilityViewSet)

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


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


urlpatterns = [
    # Аутентифікація
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Підключення CRUD ендпоінтів
    path('', include(router.urls)),
]