
import os
# !!! WARNING: DESTRUCTIVE SCRIPT !!!
# This script modifies or deletes database records.
# Do not run unless you understand the consequences.
# Backup your database before execution.

import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.subscription.models import SubscriptionPlan

def fix_features():
    plans = SubscriptionPlan.objects.all()
    for plan in plans:
        if not isinstance(plan.features, list):
            print(f"Fixing plan {plan.code}: Features was {type(plan.features)} -> {plan.features}")
            if isinstance(plan.features, dict):
                # If it's a dict, maybe we can extract a value, or just reset to empty list
                # Or maybe it's just invalid.
                # Let's see if there is a 'features' key inside?
                if 'features' in plan.features and isinstance(plan.features['features'], list):
                    plan.features = plan.features['features']
                else:
                    # Default for Free Trial or others?
                    if 'FREE' in plan.code or 'TRIAL' in plan.code:
                        plan.features = [
                            "7 Days Validity",
                            "1 Owner & 1 Staff",
                            "20 Products",
                            "50 Invoices",
                            "Basic Reports"
                        ]
                    else:
                         plan.features = [] # Fallback
            else:
                 plan.features = []
            
            plan.save()
            print(f"Plan {plan.code} updated to list.")
        else:
            print(f"Plan {plan.code} is already a list.")

if __name__ == '__main__':
    fix_features()
