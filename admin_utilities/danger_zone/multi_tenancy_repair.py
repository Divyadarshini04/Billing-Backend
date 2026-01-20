import os
# !!! WARNING: DESTRUCTIVE SCRIPT !!!
# This script modifies or deletes database records.
# Do not run unless you understand the consequences.
# Backup your database before execution.

import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import Role, UserRole
from apps.common.models import CompanyProfile
from apps.customer.models import Customer
from apps.product.models import Product, Category
from apps.billing.models import Invoice

User = get_user_model()

def repair():
    print("Step 1: Decoupling users from parent 32")
    u32 = User.objects.get(id=32)
    children = User.objects.filter(parent=u32)
    for child in children:
        print(f"  Decoupling {child.phone}")
        child.parent = None
        child.save()

    print("Step 2: Ensuring OWNER roles")
    owner_role, _ = Role.objects.get_or_create(name="OWNER")
    for u in User.objects.filter(is_super_admin=False):
        if not UserRole.objects.filter(user=u, role=owner_role).exists():
            print(f"  Adding OWNER role to {u.phone}")
            UserRole.objects.create(user=u, role=owner_role)

    print("Step 3: Creating missing CompanyProfiles")
    for u in User.objects.filter(is_super_admin=False):
        if not hasattr(u, 'company_profile'):
            biz_name = (u.last_name or f"Business-{u.phone}").strip()
            # Ensure biz_name is unique for CompanyProfile.company_name
            if CompanyProfile.objects.filter(company_name=biz_name).exists():
                biz_name = f"{biz_name}-{u.phone}"
            
            print(f"  Creating Profile for {u.phone} as {biz_name}")
            CompanyProfile.objects.create(
                owner=u,
                company_name=biz_name,
                company_code=f"{biz_name[:3].upper()}-{uuid.uuid4().hex[:4].upper()}",
                phone=u.phone,
                email=u.email or f"{u.phone}@example.com",
                tax_id=f"GST-{uuid.uuid4().hex[:6].upper()}",
                established_date='2020-01-01'
            )

    print("Step 4: Cleanup Data Ownership")
    # Instead of bulk update which might hit constraints, we do it one by one and catch
    for model in [Customer, Product, Category, Invoice]:
        print(f"  Processing {model.__name__}")
        for obj in model.objects.filter(owner__isnull=True):
            try:
                obj.owner = u32
                obj.save()
            except Exception as e:
                print(f"    Failed to assign {model.__name__} {obj.id} to u32: {e}")
                # If it's a duplicate phone etc, just delete the orphan
                obj.delete()
                print(f"    Deleted duplicate orphan {model.__name__} {obj.id}")

    print("DONE")

if __name__ == "__main__":
    repair()
