from django.core.management.base import BaseCommand
from apps.subscription.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Seeds the database with initial subscription plans'

    def handle(self, *args, **kwargs):
        plans = [
            {
                "code": "free_trial",
                "name": "Free Trial",
                "price": 0,
                "duration_days": 7,
                "max_staff_users": 2,
                "business_limit": "1",
                "branch_limit": "1",
                "invoice_limit": "100",
                "description": "Best for: First-time users who want to test the system",
                "features": [
                    "POS Billing",
                    "GST Invoice",
                    "Customer Management",
                    "Product Management",
                    "Invoice PDF & Print",
                    "Basic Dashboard"
                ]
            },
            {
                "code": "basic_monthly",
                "name": "Basic Plan (Monthly)",
                "price": 699,
                "duration_days": 30,
                "max_staff_users": 3,
                "business_limit": "1",
                "branch_limit": "1",
                "invoice_limit": "1000",
                "description": "Best for: Small shops & startups",
                "features": [
                    "POS Billing",
                    "GST Invoices",
                    "Customer Management",
                    "Pending Amount Tracking",
                    "Basic Sales Reports",
                    "Invoice PDF & Print",
                    "Email Support"
                ]
            },
            {
                "code": "basic_yearly",
                "name": "Basic Plan (Yearly)",
                "price": 6999,
                "duration_days": 365,
                "max_staff_users": 3,
                "business_limit": "1",
                "branch_limit": "1",
                "invoice_limit": "1000",
                "description": "Best for: Small shops & startups (Save ~17%)",
                "features": [
                    "POS Billing",
                    "GST Invoices",
                    "Customer Management",
                    "Pending Amount Tracking",
                    "Basic Sales Reports",
                    "Invoice PDF & Print",
                    "Email Support"
                ]
            },
            {
                "code": "standard_monthly",
                "name": "Standard Plan (Monthly)",
                "price": 1999,
                "duration_days": 30,
                "max_staff_users": 10,
                "business_limit": "1",
                "branch_limit": "3",
                "invoice_limit": "Unlimited",
                "description": "Best for: Growing businesses",
                "features": [
                    "Everything in Basic",
                    "Loyalty Points System",
                    "Discounts & Coupons",
                    "Partial Payments",
                    "Stock Alerts",
                    "WhatsApp Invoice Sharing",
                    "Advanced GST Reports",
                    "Excel Export"
                ]
            },
            {
                 "code": "standard_yearly",
                 "name": "Standard Plan (Yearly)",
                 "price": 19999,
                 "duration_days": 365,
                 "max_staff_users": 10,
                 "business_limit": "1",
                 "branch_limit": "3",
                 "invoice_limit": "Unlimited",
                 "description": "Best for: Growing businesses (Save ~17%)",
                 "features": [
                     "Everything in Basic",
                     "Loyalty Points System",
                     "Discounts & Coupons",
                     "Partial Payments",
                     "Stock Alerts",
                     "WhatsApp Invoice Sharing",
                     "Advanced GST Reports",
                     "Excel Export"
                 ]
            },
            {
                "code": "premium_monthly",
                "name": "Premium Plan (Monthly)",
                "price": 4999,
                "duration_days": 30,
                "max_staff_users": 0, # Unlimited
                "business_limit": "Multiple",
                "branch_limit": "Unlimited",
                "invoice_limit": "Unlimited",
                "description": "Best for: Large & enterprise companies",
                "features": [
                    "Everything in Standard",
                    "Multi-Branch & Multi-Business Billing",
                    "Advanced Analytics & Charts",
                    "API Access & Integrations",
                    "Custom Invoice Branding",
                    "Role-Based Permissions",
                    "Audit Logs",
                    "Priority Support"
                ]
            },
            {
                "code": "premium_yearly",
                "name": "Premium Plan (Yearly)",
                "price": 49999,
                "duration_days": 365,
                "max_staff_users": 0, # Unlimited
                "business_limit": "Multiple",
                "branch_limit": "Unlimited",
                "invoice_limit": "Unlimited",
                "description": "Best for: Large & enterprise companies (Save ~17%)",
                "features": [
                    "Everything in Standard",
                    "Multi-Branch & Multi-Business Billing",
                    "Advanced Analytics & Charts",
                    "API Access & Integrations",
                    "Custom Invoice Branding",
                    "Role-Based Permissions",
                    "Audit Logs",
                    "Priority Support"
                ]
            }
        ]

        for plan_data in plans:
            SubscriptionPlan.objects.update_or_create(
                code=plan_data['code'],
                defaults=plan_data
            )
            self.stdout.write(self.style.SUCCESS(f"Seeded plan: {plan_data['name']}"))
