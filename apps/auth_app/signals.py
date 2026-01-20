from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.subscription.models import UserSubscription, SubscriptionPlan
from apps.super_admin.models import SystemSettings

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    """
    Automatically assign a FREE trial subscription to new users (Owners)
    based on SystemSettings configuration.
    """
    if created and not instance.is_super_admin:
        try:
            # Get System Settings
            settings = SystemSettings.objects.first()
            if not settings:
                settings = SystemSettings.objects.create()
                
            trial_days = settings.default_trial_days
            
            # Get or Create FREE plan (Note: code in DB is 'free_trial')
            plan, _ = SubscriptionPlan.objects.get_or_create(
                code="free_trial",
                defaults={
                    "name": "Free Trial",
                    "price": 0.00,
                    "duration_days": trial_days,
                    "description": f"Free trial for {trial_days} days",
                    "features": {} 
                }
            )
            
            # Self-healing: Ensure Plan duration matches Settings
            if plan.duration_days != trial_days:
                print(f"DEBUG: Syncing 'free_trial' plan duration from {plan.duration_days} to {trial_days}")
                plan.duration_days = trial_days
                plan.description = f"Free trial for {trial_days} days"
                plan.save()
            
            # Create Subscription
            UserSubscription.objects.create(
                user=instance,
                plan=plan,
                status='ACTIVE',
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=trial_days),
                auto_renew=False
            )
            print(f"DEBUG: Assigned {trial_days}-day trial to {instance.phone}")
            
        except Exception as e:
            print(f"ERROR: Failed to assign trial subscription: {e}")
