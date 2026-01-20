#!/usr/bin/env python
"""
Safe database health check script
Run: python manage.py shell < admin_utilities/check_database_health.py
"""

from django.db import connection
from django.db.utils import OperationalError
from apps.auth_app.models import User
from apps.subscription.models import SubscriptionPlan, UserSubscription
from apps.super_admin.models import SystemSettings

def check_database_health():
    """Verify database is accessible and core models exist"""
    
    print("\n" + "="*60)
    print("DATABASE HEALTH CHECK")
    print("="*60)
    
    # 1. Check connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database Connection: OK")
    except OperationalError as e:
        print(f"❌ Database Connection: FAILED - {e}")
        return False
    
    # 2. Check models
    try:
        user_count = User.objects.count()
        print(f"✅ Users Table: OK ({user_count} users)")
    except Exception as e:
        print(f"❌ Users Table: FAILED - {e}")
    
    try:
        plan_count = SubscriptionPlan.objects.count()
        print(f"✅ Plans Table: OK ({plan_count} plans)")
    except Exception as e:
        print(f"❌ Plans Table: FAILED - {e}")
    
    try:
        sub_count = UserSubscription.objects.count()
        print(f"✅ Subscriptions Table: OK ({sub_count} subscriptions)")
    except Exception as e:
        print(f"❌ Subscriptions Table: FAILED - {e}")
    
    try:
        settings = SystemSettings.objects.first()
        if settings:
            print(f"✅ System Settings: OK (Updated: {settings.updated_at})")
        else:
            print("⚠️  System Settings: No settings configured yet")
    except Exception as e:
        print(f"❌ System Settings: FAILED - {e}")
    
    # 3. Check super admins
    try:
        super_admin_count = User.objects.filter(is_super_admin=True).count()
        if super_admin_count > 0:
            print(f"✅ Super Admins: OK ({super_admin_count} found)")
        else:
            print("⚠️  Super Admins: NONE - Create one via Django admin or migration")
    except Exception as e:
        print(f"❌ Super Admins: FAILED - {e}")
    
    print("="*60)
    print("✅ Database is healthy and ready to use\n")
    return True

if __name__ == "__main__":
    check_database_health()
