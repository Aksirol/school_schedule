from django.core.management.base import BaseCommand
from datetime import date, time
from schedule.models import AcademicYear, TimeSlot, Subject, Room, SchoolClass


class Command(BaseCommand):
    help = 'Seeds the database with initial data for TimeSlots, AcademicYears, Subjects, Rooms'

    def handle(self, *args, **kwargs):
        # 1. Навчальний рік
        year, created = AcademicYear.objects.get_or_create(
            name='2023-2024',
            defaults={'start_date': date(2023, 9, 1), 'end_date': date(2024, 5, 31)}
        )
        self.stdout.write(self.style.SUCCESS(f"Year {year} initialized."))

        # 2. Часові слоти (Уроки 1-7 для ПН-ПТ)
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI']
        times = [
            (time(8, 30), time(9, 15)),  # Урок 1
            (time(9, 25), time(10, 10)),  # Урок 2
            (time(10, 30), time(11, 15)),  # Урок 3
            (time(11, 35), time(12, 20)),  # Урок 4
            (time(12, 30), time(13, 15)),  # Урок 5
            (time(13, 25), time(14, 10)),  # Урок 6
            (time(14, 20), time(15, 5)),  # Урок 7
        ]

        for day in days:
            for idx, (start, end) in enumerate(times, start=1):
                TimeSlot.objects.get_or_create(
                    day_of_week=day, lesson_number=idx,
                    defaults={'start_time': start, 'end_time': end}
                )
        self.stdout.write(self.style.SUCCESS("Time slots 1-7 (Mon-Fri) initialized."))

        # 3. Предмети
        subjects = ['Математика', 'Українська мова', 'Англійська мова', 'Історія', 'Фізика', 'Інформатика']
        for sub in subjects:
            Subject.objects.get_or_create(name=sub)
        self.stdout.write(self.style.SUCCESS("Subjects initialized."))

        # 4. Кабінети
        rooms = [
            {'name': 'Каб. Математики', 'number': '101', 'cap': 30, 'type': 'Звичайний'},
            {'name': 'Комп. клас 1', 'number': '201', 'cap': 15, 'type': 'Комп\'ютерний'},
            {'name': 'Каб. Фізики', 'number': '301', 'cap': 30, 'type': 'Лабораторія'},
        ]
        for r in rooms:
            Room.objects.get_or_create(
                room_number=r['number'],
                defaults={'name': r['name'], 'capacity': r['cap'], 'room_type': r['type']}
            )
        self.stdout.write(self.style.SUCCESS("Rooms initialized."))

        # 5. Класи
        classes = [{'name': '10-А', 'grade': 10}, {'name': '11-Б', 'grade': 11}]
        for c in classes:
            SchoolClass.objects.get_or_create(
                name=c['name'],
                defaults={'grade_number': c['grade'], 'academic_year': year}
            )
        self.stdout.write(self.style.SUCCESS("Classes initialized."))