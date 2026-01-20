from django.core.management.base import BaseCommand
from apps.subscription.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Initialize default subscription plans'

    def handle(self, *args, **kwargs):
        plans = [
            {
                "code": "FREE",
                "name": "Free Trial",
                "price": 0.00,
                "duration_days": 90,
                "features": {
                    "maxProducts": 100,
                    "maxCustomers": 50,
                    "maxInvoices": 500,
                    "maxUsers": 1,
                    "storageGB": 1,
                    "reportAccess": False,
                    "advancedAnalytics": False,
                },
                "description": "3 months free trial for new users"
            },
            {
                "code": "BASIC",
                "name": "Basic Plan",
                "price": 999.00,
                "duration_days": 30,
                "features": {
                    "maxProducts": 1000,
                    "maxCustomers": 500,
                    "maxInvoices": 10000,
                    "maxUsers": 10,
                    "storageGB": 5,
                    "reportAccess": True,
                    "advancedAnalytics": False,
                },
                "description": "Perfect for small businesses"
            },
            {
                "code": "PREMIUM",
                "name": "Premium Plan",
                "price": 2999.00,
                "duration_days": 30,
                "features": {
                    "maxProducts": 5000,
                    "maxCustomers": 5000,
                    "maxInvoices": 100000,
                    "maxUsers": 100,
                    "storageGB": 50,
                    "reportAccess": True,
                    "advancedAnalytics": True,
                },
                "description": "For growing businesses with advanced needs"
            }
        ]

        for p in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                code=p['code'],
                defaults=p
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.name}'))
            else:
                self.stdout.write(f'Plan already exists: {plan.name}')

        self.stdout.write(self.style.SUCCESS('Subscription plans initialized successfully'))
