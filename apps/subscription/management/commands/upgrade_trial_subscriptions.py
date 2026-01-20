"""Django management command to auto-upgrade expired Free Trial subscriptions"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.subscription.models import SubscriptionPlan, UserSubscription

class Command(BaseCommand):
    help = 'Auto-upgrade expired Free Trial subscriptions to Basic plan'

    def handle(self, *args, **options):
        """Handle the command execution"""
        self.stdout.write(self.style.SUCCESS('Starting trial-to-basic auto-upgrade...'))
        
        try:
            free_trial_plan = SubscriptionPlan.objects.get(code='FREE')
            basic_plan = SubscriptionPlan.objects.get(code='BASIC')
        except SubscriptionPlan.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'Required subscription plan not found - {e}'))
            return
        
        # Find expired Free Trial subscriptions
        expired_trials = UserSubscription.objects.filter(
            plan=free_trial_plan,
            status='EXPIRED',
            end_date__lte=timezone.now()
        )
        
        self.stdout.write(f'Found {expired_trials.count()} expired Free Trial subscriptions')
        
        upgraded_count = 0
        for subscription in expired_trials:
            try:
                # Update to Basic subscription
                subscription.plan = basic_plan
                subscription.status = 'ACTIVE'
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=basic_plan.duration_days)
                subscription.auto_renew = False
                subscription.save()
                
                upgraded_count += 1
                user = subscription.user
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Upgraded {user.phone} ({user.first_name} {user.last_name}) to Basic plan'
                    )
                )
                
            except Exception as e:
                user = subscription.user
                self.stdout.write(
                    self.style.ERROR(f'✗ Error upgrading {user.phone}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal upgraded: {upgraded_count}')
        )
