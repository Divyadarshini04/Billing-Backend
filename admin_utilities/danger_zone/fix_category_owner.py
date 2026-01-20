import os
# !!! WARNING: DESTRUCTIVE SCRIPT !!!
# This script modifies or deletes database records.
# Do not run unless you understand the consequences.
# Backup your database before execution.

import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.product.models import Category
from django.contrib.auth import get_user_model

User = get_user_model()

def fix_category_owner():
    # 1. Get User 32 (Super Admin/Owner Context)
    try:
        owner_user = User.objects.get(id=32)
        print(f"Assigning unowned categories to: {owner_user.first_name} {owner_user.last_name} (ID: 32)")
    except User.DoesNotExist:
        print("User 32 not found. Cannot proceed.")
        return

    # 2. Find categories with owner=None
    orphaned = Category.objects.filter(owner__isnull=True)
    print(f"Found {orphaned.count()} unowned categories.")
    
    for cat in orphaned:
        print(f"Updating '{cat.name}'...")
        cat.owner = owner_user
        cat.save()
        print("  - Done.")

if __name__ == '__main__':
    fix_category_owner()
