'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import api from '@/lib/api';

// --- Типи даних ---
interface ScheduleItem {
  id: number;
  subject_name: string;
  teacher_name: string;
  class_name: string;
  room: number;
  room_number: string;
  day_of_week: string;
  lesson_number: number;
  is_published: boolean;
}

interface SchoolClass {
  id: number;
  name: string;
}

interface Teacher {
  id: number;
  first_name: string;
  last_name: string;
}

interface TimeSlot {
  id: number;
  day_of_week: string;
  lesson_number: number;
}

const DAYS = [
  { key: 'MON', label: 'Понеділок' },
  { key: 'TUE', label: 'Вівторок' },
  { key: 'WED', label: 'Середа' },
  { key: 'THU', label: 'Четвер' },
  { key: 'FRI', label: 'П\'ятниця' },
];
const LESSONS = [1, 2, 3, 4, 5, 6, 7];

export default function SchedulePage() {
  const router = useRouter();

  // Стан для розкладу
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Стан для фільтрів та мапінгу слотів
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([]);

  const [selectedClass, setSelectedClass] = useState<string>('');
  const [selectedTeacher, setSelectedTeacher] = useState<string>('');

  // 1. Завантаження довідників
  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const [classesRes, teachersRes, slotsRes] = await Promise.all([
          api.get('/classes/'),
          api.get('/teachers/'),
          api.get('/timeslots/')
        ]);
        setClasses(classesRes.data);
        setTeachers(teachersRes.data);
        setTimeSlots(slotsRes.data);
      } catch (err) {
        console.error('Помилка завантаження довідників', err);
      }
    };
    fetchFilters();
  }, []);

  // 2. Завантаження розкладу
  const fetchSchedule = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ is_published: 'true' });
      if (selectedClass) params.append('curriculum__school_class', selectedClass);
      if (selectedTeacher) params.append('curriculum__teacher', selectedTeacher);

      const response = await api.get(`/schedules/?${params.toString()}`);
      // Підтримка пагінації (results) або звичайного масиву
      setSchedules(response.data.results || response.data);
    } catch (err) {
      setError('Не вдалося завантажити розклад. Перевірте з\'єднання.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedClass, selectedTeacher]);

  useEffect(() => {
    const token = Cookies.get('access_token');
    if (!token) {
      router.push('/login');
      return;
    }
    fetchSchedule();
  }, [fetchSchedule, router]);

  const handleLogout = () => {
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
    router.push('/');
  };

  // ВИПРАВЛЕНО: Тепер повертає масив усіх уроків для конкретної клітинки
  const getLessons = (day: string, lessonNum: number) => {
    return schedules.filter(
      (s) => s.day_of_week === day && s.lesson_number === lessonNum
    );
  };

  // --- DRAG & DROP Логіка ---
  const handleDragStart = (e: React.DragEvent, scheduleId: number) => {
    e.dataTransfer.setData('scheduleId', scheduleId.toString());
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent, targetDay: string, targetLessonNum: number) => {
    e.preventDefault();
    const scheduleId = e.dataTransfer.getData('scheduleId');
    if (!scheduleId) return;

    const targetSlot = timeSlots.find(
      (ts) => ts.day_of_week === targetDay && ts.lesson_number === targetLessonNum
    );

    if (!targetSlot) {
      setError('Помилка: Не знайдено цільовий часовий слот.');
      return;
    }

    const currentLesson = schedules.find((s) => s.id.toString() === scheduleId);
    if (!currentLesson) return;

    setIsLoading(true);

    try {
      await api.post(`/schedules/${scheduleId}/manual_move/`, {
        new_time_slot_id: targetSlot.id,
        new_room_id: currentLesson.room,
        reason: 'Ручне коригування розкладу (Drag & Drop)'
      });

      await fetchSchedule();
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Помилка при перенесенні уроку.';
      alert(`Відхилено: ${errorMsg}`);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">

        {/* Шапка */}
        <div className="flex justify-between items-center mb-6 bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <h1 className="text-2xl font-bold text-gray-800">Розклад занять</h1>
          <button
            onClick={handleLogout}
            className="text-sm bg-red-50 text-red-600 px-4 py-2 rounded hover:bg-red-100 transition font-medium"
          >
            Вийти
          </button>
        </div>

        {/* Панель фільтрів */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 mb-6 flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Фільтр по класу</label>
            <select
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 text-gray-700"
            >
              <option value="">Всі класи</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Фільтр по вчителю</label>
            <select
              value={selectedTeacher}
              onChange={(e) => setSelectedTeacher(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 text-gray-700"
            >
              <option value="">Всі вчителі</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>{t.last_name} {t.first_name}</option>
              ))}
            </select>
          </div>

          <div className="flex-none">
            <button
              onClick={() => { setSelectedClass(''); setSelectedTeacher(''); }}
              className="bg-gray-100 text-gray-600 px-4 py-2 rounded-md hover:bg-gray-200 transition font-medium text-sm"
            >
              Скинути фільтри
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 text-red-700 p-4 rounded mb-6">{error}</div>
        )}

        {/* Сітка розкладу */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden relative min-h-[400px]">

          {isLoading && (
            <div className="absolute inset-0 bg-white/60 backdrop-blur-sm flex items-center justify-center z-10">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-100 text-gray-700 text-sm uppercase tracking-wider">
                  <th className="p-4 border-b border-gray-200 font-semibold w-24 text-center">Урок</th>
                  {DAYS.map((day) => (
                    <th key={day.key} className="p-4 border-b border-gray-200 font-semibold min-w-[200px]">
                      {day.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="text-gray-800 divide-y divide-gray-100">
                {LESSONS.map((lessonNum) => (
                  <tr key={lessonNum} className="hover:bg-gray-50 transition">
                    <td className="p-4 border-r border-gray-100 text-center font-bold text-gray-500 bg-gray-50">
                      {lessonNum}
                    </td>
                    {DAYS.map((day) => {
                      // ВИПРАВЛЕНО: Отримуємо МАСИВ уроків
                      const lessonsInCell = getLessons(day.key, lessonNum);
                      return (
                        <td
                          key={`${day.key}-${lessonNum}`}
                          className="p-3 border-r border-gray-100 align-top min-h-[7rem] border-dashed hover:bg-blue-50/50 transition-colors"
                          onDragOver={handleDragOver}
                          onDrop={(e) => handleDrop(e, day.key, lessonNum)}
                        >
                          {lessonsInCell.length > 0 ? (
                            <div className="flex flex-col gap-2 h-full">
                              {/* Рендеримо кожен урок як окрему картку */}
                              {lessonsInCell.map((lesson) => (
                                <div
                                  key={lesson.id}
                                  draggable
                                  onDragStart={(e) => handleDragStart(e, lesson.id)}
                                  className="bg-blue-50 border border-blue-200 rounded-md p-3 flex flex-col justify-between shadow-sm hover:shadow-md transition cursor-grab active:cursor-grabbing hover:border-blue-400"
                                >
                                  <div>
                                    <div className="font-semibold text-blue-900 leading-tight">
                                      {lesson.subject_name}
                                    </div>
                                    <div className="text-xs text-blue-600 mt-1 font-medium">
                                      {lesson.class_name}
                                    </div>
                                  </div>
                                  <div className="flex justify-between items-end mt-2 text-xs text-gray-500">
                                    <span className="truncate pr-2">{lesson.teacher_name}</span>
                                    <span className="font-medium bg-white px-1.5 py-0.5 rounded shadow-sm text-gray-700 border border-gray-100">
                                      Каб. {lesson.room_number}
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="h-full w-full flex items-center justify-center text-gray-300 text-xs italic py-6">
                              Вільне вікно
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}