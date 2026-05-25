from celery import shared_task
from .engine import generate_schedule_engine


@shared_task(bind=True)
def run_schedule_generation(self, academic_year_id):
    # Оновлюємо статус задачі, щоб клієнт міг його читати
    self.update_state(state='PROGRESS', meta={'message': 'Алгоритм працює...'})

    result = generate_schedule_engine(academic_year_id)

    return result