import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import Role, UserRole
from apps.common.models import CompanyProfile

User = get_user_model()

print("--- USER & COMPANY MAPPING ---")
users = User.objects.all()
for u in users:
    roles = [ur.role.name for ur in UserRole.objects.filter(user=u)]
    if u.is_super_admin:
        roles.append("SUPERADMIN")
    
    parent_info = f"Parent: {u.parent.phone}" if u.parent else "No Parent"
    print(f"User: {u.phone} | Roles: {roles} | {parent_info} | First: {u.first_name}")
    
    # Check for direct company profile
    profile = CompanyProfile.objects.filter(owner=u).first()
    if profile:
        print(f"  -> OWNS PROFILE: {profile.company_name} (Active: {profile.is_active})")
        print(f"     Address: {profile.street_address}, {profile.city}, {profile.state}")
    
print("\n--- ALL COMPANY PROFILES ---")
profiles = CompanyProfile.objects.all()
for p in profiles:
    owner_phone = p.owner.phone if p.owner else "None"
    print(f"Profile: {p.company_name} | Owner: {owner_phone} | Active: {p.is_active}")
