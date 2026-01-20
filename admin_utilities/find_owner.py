import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import Role

User = get_user_model()

try:
    owner_role = Role.objects.get(name='OWNER')
    owners = User.objects.filter(user_roles__role=owner_role)
    if owners.exists():
        for owner in owners:
            print(f"OWNER_PHONE={owner.phone}")
    else:
        # Check if there are any users at all
        all_users = User.objects.all()
        print(f"Total Users: {all_users.count()}")
        for u in all_users:
            roles = [r.name for r in Role.objects.filter(role_users__user=u)]
            print(f"User: {u.phone}, Roles: {roles}")
except Exception as e:
    print(f"Error: {e}")
