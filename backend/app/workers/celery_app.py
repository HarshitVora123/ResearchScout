"""Celery application configuration for background task processing."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "researchscout",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing — separate queues for different workloads
    # Note: task-level queue= decorators override these routes.
    # The extract queue is set on extract_and_store via its decorator.
    task_routes={
        "app.workers.crawl_worker.crawl_url": {"queue": "crawl"},
        "app.workers.crawl_worker.crawl_scheduled_sources": {"queue": "crawl"},
        "app.workers.crawl_worker.batch_crawl_urls": {"queue": "crawl"},
        "app.workers.crawl_worker.extract_and_store": {"queue": "extract"},
        "app.workers.crawl_worker.expire_old_opportunities": {"queue": "default"},
        "app.workers.embedding_worker.*": {"queue": "embed"},
        "app.workers.notification_worker.*": {"queue": "default"},
    },

    # Reliability
    task_acks_late=True,       # Ack after task completes (not at start)
    worker_prefetch_multiplier=1,  # One task at a time per worker
    task_reject_on_worker_lost=True,

    # Timeouts
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,       # 10 minutes hard limit

    # Result expiration
    result_expires=86400,      # 24 hours

    # Beat schedule — periodic tasks
    beat_schedule={
        "crawl-scheduled-sources": {
            "task": "app.workers.crawl_worker.crawl_scheduled_sources",
            "schedule": crontab(hour="*/6"),  # Every 6 hours
        },
        "expire-old-opportunities": {
            "task": "app.workers.crawl_worker.expire_old_opportunities",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
        "generate-daily-digest": {
            "task": "app.workers.notification_worker.send_daily_digest",
            "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM
        },
    },
)

# Auto-discover tasks from worker modules
celery_app.autodiscover_tasks([
    "app.workers.crawl_worker",
    "app.workers.embedding_worker",
    "app.workers.notification_worker",
])
