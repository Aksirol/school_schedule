from schedule.models import Curriculum, Schedule, TimeSlot, Room, TeacherAvailability
import time
import collections


def generate_schedule_engine(academic_year_id):
    start_time = time.time()

    Schedule.objects.filter(curriculum__academic_year_id=academic_year_id, is_published=False).delete()

    curriculums = Curriculum.objects.filter(academic_year_id=academic_year_id).order_by('-hours_per_week')
    all_time_slots = list(TimeSlot.objects.all().order_by('day_of_week', 'lesson_number'))
    all_rooms = list(Room.objects.all())

    unresolved_conflicts = []
    created_schedules = []

    occupied_class_slots = set()
    occupied_teacher_slots = set()
    occupied_room_slots = set()

    # Відстеження кількості уроків на день для санітарних норм та рівномірності
    class_daily_lessons = collections.defaultdict(int)

    unavailable_teachers = set(
        TeacherAvailability.objects.filter(status='UNAVAILABLE')
        .values_list('teacher_id', 'time_slot_id')
    )

    # 1. Правила типів кабінетів
    room_requirements = {
        'Інформатика': 'Комп\'ютерний',
        'Фізика': 'Лабораторія',
        'Хімія': 'Лабораторія',
        'Біологія': 'Лабораторія',
        'Фізична культура': 'Спортзал'
    }

    # 2. Санітарні норми (макс. уроків на день)
    def get_max_lessons(grade):
        if grade <= 4: return 5
        if grade <= 9: return 6
        return 7

    for curr in curriculums:
        req_room_type = room_requirements.get(curr.subject.name, 'Звичайний')
        max_daily_lessons = get_max_lessons(curr.school_class.grade_number)

        for _ in range(curr.hours_per_week):
            slot_found = False

            # 3. РІВНОМІРНІСТЬ: Сортуємо дні тижня так, щоб спочатку йшли ті дні,
            # де у цього класу зараз найменше уроків.
            days = ['MON', 'TUE', 'WED', 'THU', 'FRI']
            days.sort(key=lambda d: class_daily_lessons[(curr.school_class_id, d)])

            for day in days:
                if slot_found: break

                # Перевірка санітарних норм
                if class_daily_lessons[(curr.school_class_id, day)] >= max_daily_lessons:
                    continue

                day_slots = [s for s in all_time_slots if s.day_of_week == day]

                for slot in day_slots:
                    # Конфлікти зайнятості
                    if (curr.school_class_id, slot.id) in occupied_class_slots: continue
                    if (curr.teacher_id, slot.id) in occupied_teacher_slots: continue
                    if (curr.teacher_id, slot.id) in unavailable_teachers: continue

                    # Пошук кабінету відповідно до типу
                    available_room = None
                    for room in all_rooms:
                        # Шукаємо ідеальний кабінет
                        if room.room_type == req_room_type and (room.id, slot.id) not in occupied_room_slots:
                            available_room = room
                            break

                    # Фолбек: якщо предмет "Звичайний", а звичайні кабінети закінчились - беремо БУДЬ-ЯКИЙ вільний
                    if not available_room and req_room_type == 'Звичайний':
                        for room in all_rooms:
                            if (room.id, slot.id) not in occupied_room_slots:
                                available_room = room
                                break

                    if not available_room:
                        continue  # Шукаємо інший часовий слот

                    # Успіх! Створюємо урок.
                    new_lesson = Schedule(
                        curriculum=curr,
                        room=available_room,
                        time_slot=slot,
                        is_published=False
                    )
                    created_schedules.append(new_lesson)

                    occupied_class_slots.add((curr.school_class_id, slot.id))
                    occupied_teacher_slots.add((curr.teacher_id, slot.id))
                    occupied_room_slots.add((available_room.id, slot.id))
                    class_daily_lessons[(curr.school_class_id, day)] += 1

                    slot_found = True
                    break  # Переходимо до наступної години цього предмета

            if not slot_found:
                unresolved_conflicts.append(
                    f"Не знайдено слот: {curr.subject.name} ({curr.school_class.name}) - Вчитель {curr.teacher.last_name}")

    Schedule.objects.bulk_create(created_schedules)

    execution_time = time.time() - start_time
    return {
        "status": "success" if not unresolved_conflicts else "partial",
        "lessons_scheduled": len(created_schedules),
        "unresolved_conflicts": unresolved_conflicts,
        "execution_time_seconds": round(execution_time, 2)
    }