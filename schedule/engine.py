from schedule.models import Curriculum, Schedule, TimeSlot, Room, TeacherAvailability
import time


def generate_schedule_engine(academic_year_id):
    start_time = time.time()

    # 1. Очищуємо старий розклад для цього року (неопублікований)
    Schedule.objects.filter(curriculum__academic_year_id=academic_year_id, is_published=False).delete()

    # 2. Завантажуємо базові дані
    curriculums = Curriculum.objects.filter(academic_year_id=academic_year_id).order_by('-hours_per_week')
    all_time_slots = list(TimeSlot.objects.all().order_by('day_of_week', 'lesson_number'))
    all_rooms = list(Room.objects.all())

    unresolved_conflicts = []
    created_schedules = []

    # -- ВІДСТЕЖЕННЯ ЗАЙНЯТОСТІ В ПАМ'ЯТІ (Надшвидкий пошук через Hash Sets) --
    # Формат: (суть_id, time_slot_id)
    occupied_class_slots = set()
    occupied_teacher_slots = set()
    occupied_room_slots = set()

    # Кешуємо недоступність вчителів, щоб не робити запити в БД у циклі
    unavailable_teachers = set(
        TeacherAvailability.objects.filter(status='UNAVAILABLE')
        .values_list('teacher_id', 'time_slot_id')
    )

    for curr in curriculums:
        for _ in range(curr.hours_per_week):
            slot_found = False

            for slot in all_time_slots:
                # Перевірка 1: Чи немає вже у цього класу уроку в цей час?
                if (curr.school_class_id, slot.id) in occupied_class_slots:
                    continue

                # Перевірка 2: Чи вільний вчитель? (Чи не веде інший урок)
                if (curr.teacher_id, slot.id) in occupied_teacher_slots:
                    continue

                # Перевірка 3: Чи не поставив вчитель статус "Недоступний"
                if (curr.teacher_id, slot.id) in unavailable_teachers:
                    continue

                # Перевірка 4: Шукаємо вільний кабінет
                available_room = None
                for room in all_rooms:
                    if (room.id, slot.id) not in occupied_room_slots:
                        available_room = room
                        break

                if not available_room:
                    continue  # Немає вільних кабінетів

                # Якщо всі перевірки пройдені — створюємо запис!
                new_lesson = Schedule(
                    curriculum=curr,
                    room=available_room,
                    time_slot=slot,
                    is_published=False
                )
                created_schedules.append(new_lesson)

                # -- ФІКСУЄМО СЛОТИ ЯК ЗАЙНЯТІ ДЛЯ НАСТУПНИХ ІТЕРАЦІЙ --
                occupied_class_slots.add((curr.school_class_id, slot.id))
                occupied_teacher_slots.add((curr.teacher_id, slot.id))
                occupied_room_slots.add((available_room.id, slot.id))

                slot_found = True
                break  # Урок успішно поставлено, переходимо до наступної години

            if not slot_found:
                unresolved_conflicts.append(
                    f"Не вдалося знайти місце для: {curr.subject.name} ({curr.school_class.name}) - Вчитель {curr.teacher.last_name}")

    # Зберігаємо все одним батчем для швидкості
    Schedule.objects.bulk_create(created_schedules)

    execution_time = time.time() - start_time

    return {
        "status": "success" if not unresolved_conflicts else "partial",
        "lessons_scheduled": len(created_schedules),
        "unresolved_conflicts": unresolved_conflicts,
        "execution_time_seconds": round(execution_time, 2)
    }