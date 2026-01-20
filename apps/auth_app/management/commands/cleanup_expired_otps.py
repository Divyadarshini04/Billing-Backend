"""
Management command to cleanup expired and used OTPs from database.
Run periodically via Django management command or scheduled task.

Usage:
    python manage.py cleanup_expired_otps

For Windows Task Scheduler:
    python manage.py cleanup_expired_otps >> logs/otp_cleanup.log 2>&1

For Celery Beat, add to celery.py:
    from celery.schedules import crontab
    app.conf.beat_schedule = {
        'cleanup-expired-otps': {
            'task': 'apps.auth_app.tasks.cleanup_expired_otps',
            'schedule': crontab(minute='*/30'),  # Every 30 minutes
        },
    }
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.auth_app.models import OTP

class Command(BaseCommand):
    help = "Delete expired and used OTPs from database"

    def add_arguments(self, parser):
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=1,
            help='Delete OTPs older than N days (default: 1)',
        )

    def handle(self, *args, **options):
        older_than_days = options.get('older_than_days', 1)
        now = timezone.now()
        
        # Delete expired OTPs using the model manager
        deleted_count = OTP.delete_old()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Successfully deleted {deleted_count} expired/used OTP records"
            )
        )
