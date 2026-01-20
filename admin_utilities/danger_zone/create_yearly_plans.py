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

def create_yearly_plans():
    monthly_plans = SubscriptionPlan.objects.filter(duration_days=30)
    
    created_count = 0
    
    for plan in monthly_plans:
        yearly_code = f"{plan.code}_YEARLY"
        
        # Check if yearly plan already exists
        if SubscriptionPlan.objects.filter(code=yearly_code).exists():
            print(f"Yearly plan for {plan.name} ({yearly_code}) already exists.")
            continue
            
        print(f"Creating yearly plan for {plan.name}...")
        
        # Calculate yearly price (10 months price = ~17% discount)
        yearly_price = plan.price * 10
        
        SubscriptionPlan.objects.create(
            name=f"{plan.name} (Yearly)", # Adding suffix just in case, though frontend cleans it
            code=yearly_code,
            price=yearly_price,
            duration_days=365,
            currency=plan.currency,
            description=plan.description,
            features=plan.features,
            max_staff_users=plan.max_staff_users,
            invoice_limit=plan.invoice_limit,
            business_limit=plan.business_limit,
            branch_limit=plan.branch_limit,
            is_active=plan.is_active
        )
        created_count += 1
        
    # Also ensure current plans have (Monthly) in name if preferred, 
    # but based on frontend logic `plan.name.replace...` it handles bare names too.
    # However, to be consistent let's update monthly plans to have (Monthly) suffix if they don't?
    # Actually, the frontend strip logic implies it expects them. 
    # But if I leave it as "Premium", it displays as "Premium". 
    # If I name the yearly one "Premium (Yearly)", it displays as "Premium".
    # So that works.
    
    print(f"Successfully created {created_count} yearly plans.")

if __name__ == "__main__":
    create_yearly_plans()
