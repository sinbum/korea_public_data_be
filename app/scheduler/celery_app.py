from celery import Celery
from ..core.config import settings

celery_app = Celery(
    "korea_public_api",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['app.scheduler.tasks']
)

# Celery 설정
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    
    # 스케줄 설정
    beat_schedule={
        'fetch-announcements-daily': {
            'task': 'app.scheduler.tasks.fetch_all_announcements',
            'schedule': 60.0 * 60.0 * 24,  # 매일 실행
            'options': {'queue': 'data_collection'}
        },
        'fetch-contents-daily': {
            'task': 'app.scheduler.tasks.fetch_all_contents',
            'schedule': 60.0 * 60.0 * 24,  # 매일 실행
            'options': {'queue': 'data_collection'}
        },
        'fetch-statistics-weekly': {
            'task': 'app.scheduler.tasks.fetch_all_statistics',
            'schedule': 60.0 * 60.0 * 24 * 7,  # 매주 실행
            'options': {'queue': 'data_collection'}
        },
        'fetch-businesses-weekly': {
            'task': 'app.scheduler.tasks.fetch_all_businesses',
            'schedule': 60.0 * 60.0 * 24 * 7,  # 매주 실행
            'options': {'queue': 'data_collection'}
        }
    },
    task_routes={
        'app.scheduler.tasks.*': {'queue': 'data_collection'}
    }
)