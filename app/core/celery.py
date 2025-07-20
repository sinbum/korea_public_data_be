from celery import Celery
from .config import settings

# Celery 앱 생성
celery_app = Celery(
    "korea_public_api",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.domains.announcements.tasks",
        # "app.domains.data_sources.tasks",  # TODO: 추후 추가
    ]
)

# Celery 설정
celery_app.conf.update(
    # 작업 시간 제한 (초)
    task_time_limit=30 * 60,  # 30분
    task_soft_time_limit=25 * 60,  # 25분
    
    # 작업 직렬화
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 시간대 설정
    timezone="Asia/Seoul",
    enable_utc=True,
    
    # 작업 결과 설정
    result_expires=60 * 60 * 24,  # 24시간
    result_backend_transport_options={
        "retry_on_timeout": True,
        "retry_on_connection_error": True,
    },
    
    # 워커 설정
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # 라우팅
    task_routes={
        "app.domains.announcements.tasks.*": {"queue": "announcements"},
        "app.domains.data_sources.tasks.*": {"queue": "data_sources"},
    },
    
    # 스케줄 설정 (Celery Beat)
    beat_schedule={
        "fetch-announcements-daily": {
            "task": "app.domains.announcements.tasks.fetch_announcements_task",
            "schedule": 60.0 * 60.0 * 24.0,  # 매일 실행
            "options": {"queue": "announcements"}
        },
    },
    
    # 기본 큐
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)

# 자동 작업 발견
celery_app.autodiscover_tasks()

if __name__ == "__main__":
    celery_app.start()