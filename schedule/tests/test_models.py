from django.test import TestCase
from datetime import date, time
from schedule.models import AcademicYear, SchoolClass, Room, TimeSlot

class ModelTests(TestCase):
    def test_create_academic_year(self):
        """Перевірка створення навчального року"""
        year = AcademicYear.objects.create(
            name="2023-2024",
            start_date=date(2023, 9, 1),
            end_date=date(2024, 5, 31)
        )
        self.assertEqual(year.name, "2023-2024")
        self.assertEqual(str(year), "2023-2024")

    def test_create_room(self):
        """Перевірка створення кабінету та його відображення"""
        room = Room.objects.create(
            name="Каб. Фізики",
            room_number="301",
            capacity=30,
            room_type="Лабораторія"
        )
        self.assertEqual(room.capacity, 30)
        self.assertEqual(str(room), "Каб. 301 - Каб. Фізики")

    def test_timeslot_unique_constraint(self):
        """Перевірка унікальності часового слоту (номер уроку + день)"""
        TimeSlot.objects.create(
            lesson_number=1, day_of_week='MON',
            start_time=time(8, 30), end_time=time(9, 15)
        )
        # Спроба створити ще один 1-й урок у понеділок має викликати помилку
        with self.assertRaises(Exception):
            TimeSlot.objects.create(
                lesson_number=1, day_of_week='MON',
                start_time=time(9, 25), end_time=time(10, 10)
            )