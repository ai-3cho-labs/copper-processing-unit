"""
$COPPER Celery Application

Celery configuration for background task processing.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "copper",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0",
    include=[
        "app.tasks.snapshot_task",
        "app.tasks.buyback_task",
        "app.tasks.distribution_task",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minute hard limit
    task_soft_time_limit=240,  # 4 minute soft limit
    worker_prefetch_multiplier=1,  # One task at a time
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    # Maybe take snapshot (40% chance) - every hour
    "maybe-snapshot": {
        "task": "app.tasks.snapshot_task.maybe_take_snapshot",
        "schedule": crontab(minute=0),  # Every hour at :00
    },
    # Process creator rewards and execute buybacks - every 15 minutes
    "process-rewards": {
        "task": "app.tasks.buyback_task.process_creator_rewards",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Check distribution triggers - every 5 minutes
    "check-distribution": {
        "task": "app.tasks.distribution_task.check_distribution_triggers",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    # Update all tier progressions - every hour
    "update-tiers": {
        "task": "app.tasks.snapshot_task.update_all_tiers",
        "schedule": crontab(minute=30),  # Every hour at :30
    },
}
