
import os
# !!! WARNING: DESTRUCTIVE SCRIPT !!!
# This script modifies or deletes database records.
# Do not run unless you understand the consequences.
# Backup your database before execution.

import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.subscription.models import SubscriptionPlan

def update_plans():
    # Define Plans
    plans_data = [
        {
            "code": "FREE",
            "name": "Trial Plan", 
            "price": 0,
            "duration_days": 7,
            "max_staff_users": 1,
            "product_limit": "20",
            "customer_limit": "20",
            "invoice_limit": "50",
            "business_limit": "1",
            "branch_limit": "1",
            "description": "Try the system, understand flow",
            "features": [
                "1 Owner + 1 Staff (Sales Exec)",
                "Up to 20 Products",
                "Up to 20 Customers", 
                "Limited Invoices (50)",
                "Basic GST / Tax",
                "1 Device Login Only",
                "No Reports / Inventory",
                "No Support"
            ]
        },
        {
            "code": "BASIC",
            "name": "Basic Plan",
            "price": 699,
            "duration_days": 30,
            "max_staff_users": 2,
            "product_limit": "200",
            "customer_limit": "Unlimited",
            "invoice_limit": "Unlimited",
            "business_limit": "1",
            "branch_limit": "1",
            "description": "Small shops – force upgrade when staff grows",
            "features": [
                "1 Owner + 2 Staff",
                "Up to 200 Products",
                "Unlimited Customers & Invoices",
                "GST / Tax & Discounts",
                "Basic Inventory",
                "Daily Sales & Simple Reports",
                "One device per staff",
                "Limited Support"
            ]
        },
        {
            "code": "STANDARD",
            "name": "Standard Plan",
            "price": 999,
            "duration_days": 30,
            "max_staff_users": 5,
            "product_limit": "Unlimited",
            "customer_limit": "Unlimited",
            "invoice_limit": "Unlimited",
            "business_limit": "1",
            "branch_limit": "1",
            "description": "Growing businesses (Most recommended)",
            "features": [
                "1 Owner + 5 Staff",
                "Unlimited Products & Customers",
                "Unlimited Invoices",
                "Multiple Tax Slabs & Discounts",
                "Advanced Inventory (Low Stock Alerts)",
                "Detailed Reports (Product/Staff wise)",
                "Email / Chat Support"
            ]
        },
        {
            "code": "PREMIUM",
            "name": "Premium Plan",
            "price": 1999,
            "duration_days": 30,
            "max_staff_users": 0, # Unlimited
            "product_limit": "Unlimited",
            "customer_limit": "Unlimited",
            "invoice_limit": "Unlimited",
            "business_limit": "1",
            "branch_limit": "Multi-location",
            "description": "Large businesses – full control",
            "features": [
                "Unlimited Staff",
                "Unlimited Everything",
                "Advanced Tax (GST, CGST, SGST, IGST)",
                "Multi-location Stock & Alerts",
                "Advanced Reports (P&L, Tax, Export)",
                "Strict Device Binding & Security",
                "Priority Support (Phone/WhatsApp)",
                "Roles & Permissions"
            ]
        }
    ]

    for p_data in plans_data:
        print(f"Updating/Creating {p_data['name']}...")
        plan, created = SubscriptionPlan.objects.update_or_create(
            code=p_data['code'],
            defaults={
                "name": p_data['name'],
                "price": p_data['price'],
                "duration_days": p_data['duration_days'],
                "max_staff_users": p_data['max_staff_users'],
                "product_limit": p_data['product_limit'],
                "customer_limit": p_data['customer_limit'],
                "invoice_limit": p_data['invoice_limit'],
                "business_limit": p_data['business_limit'],
                "branch_limit": p_data['branch_limit'],
                "description": p_data['description'],
                "features": p_data['features'],
                "is_active": True
            }
        )
        
        # If it's a paid monthly plan, update/create the Yearly version too
        if p_data['price'] > 0 and p_data['duration_days'] == 30:
            yearly_code = f"{p_data['code']}_YEARLY"
            yearly_price = p_data['price'] * 10 # 2 months free
            yearly_name = f"{p_data['name']} (Yearly)"
            
            print(f"  -> Updating/Creating Yearly version: {yearly_name}")
            SubscriptionPlan.objects.update_or_create(
                code=yearly_code,
                defaults={
                    "name": yearly_name,
                    "price": yearly_price,
                    "duration_days": 365,
                    "max_staff_users": p_data['max_staff_users'],
                    "product_limit": p_data['product_limit'],
                    "customer_limit": p_data['customer_limit'],
                    "invoice_limit": p_data['invoice_limit'],
                    "business_limit": p_data['business_limit'],
                    "branch_limit": p_data['branch_limit'],
                    "description": p_data['description'],
                    "features": p_data['features'],
                    "is_active": True
                }
            )

    print("Plans update complete.")

if __name__ == "__main__":
    update_plans()
