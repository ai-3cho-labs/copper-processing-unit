"""
$COPPER Celery Application

Celery configuration for background task processing.
"""

import logging
from celery import Celery, Task
from celery.schedules import crontab

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseTaskWithRetry(Task):
    """
    Base task class with automatic retry configuration.

    Provides exponential backoff retry for transient errors like
    network timeouts, API rate limits, and database connection issues.
    """
    # Retry on common transient errors
    autoretry_for = (
        ConnectionError,
        TimeoutError,
        OSError,  # Network errors
    )
    # Retry configuration
    max_retries = 3
    retry_backoff = True  # Exponential backoff: 1s, 2s, 4s...
    retry_backoff_max = 300  # Cap at 5 minutes
    retry_jitter = True  # Add randomness to prevent thundering herd

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failures for monitoring."""
        logger.error(
            f"Task {self.name}[{task_id}] failed after {self.request.retries} retries: {exc}"
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Log task retries for monitoring."""
        logger.warning(
            f"Task {self.name}[{task_id}] retrying (attempt {self.request.retries + 1}/{self.max_retries}): {exc}"
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)


# Create Celery app
celery_app = Celery(
    "copper",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0",
    include=[
        "app.tasks.snapshot_task",
        "app.tasks.buyback_task",
        "app.tasks.distribution_task",
    ],
    task_cls=BaseTaskWithRetry,  # Use retry-enabled base task
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minute hard limit (increased for network congestion)
    task_soft_time_limit=300,  # 5 minute soft limit
    worker_prefetch_multiplier=1,  # One task at a time
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
    # SECURITY: Expire task results after 1 hour to limit data retention in Redis
    # Task results may contain wallet addresses and transaction data
    result_expires=3600,  # 1 hour
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
