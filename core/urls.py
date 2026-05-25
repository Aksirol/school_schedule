from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Підключаємо наші API ендпоінти
    path('api/', include('schedule.urls')),
]