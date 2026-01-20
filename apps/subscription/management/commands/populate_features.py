from django.core.management.base import BaseCommand
from apps.subscription.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Populates default features for subscription plans'

    def handle(self, *args, **kwargs):
        defaults = {
            'FREE': [
                "Basic POS System",
                "7-Day Trial",
                "Limited Transactions",
                "Email Support"
            ],
            'BASIC': [
                "Full POS System",
                "Inventory Management",
                "Sales Reports",
                "Customer Database",
                "Email Support"
            ],
            'STANDARD': [
                "Everything in Basic",
                "Advanced Analytics",
                "Customer Segmentation",
                "Staff User Management",
                "Priority Email Support"
            ],
            'PREMIUM': [
                "Everything in Standard",
                "Unlimited Staff Users",
                "Priority Support",
                "Custom Reports",
                "24/7 Phone Support",
                "Dedicated Account Manager"
            ]
        }

        for code, features in defaults.items():
            try:
                plan = SubscriptionPlan.objects.get(code=code)
                # Only update if features are empty or user asks for overwrite. 
                # Here we overwrite to ensure they see data.
                plan.features = features
                plan.save()
                self.stdout.write(self.style.SUCCESS(f'Updated features for {code}'))
            except SubscriptionPlan.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Plan {code} not found'))
