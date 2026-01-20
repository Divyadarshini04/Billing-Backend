#!/usr/bin/env python
"""
Safe user management utilities
Run: python manage.py shell
Then: exec(open('admin_utilities/user_management.py').read())
"""

from apps.auth_app.models import User
import getpass

def create_super_admin():
    """Safely create a new Super Admin user"""
    print("\n" + "="*60)
    print("CREATE SUPER ADMIN - PLEASE CONFIRM")
    print("="*60)
    
    phone = input("Enter phone number: ").strip()
    first_name = input("Enter first name: ").strip()
    last_name = input("Enter last name: ").strip()
    email = input("Enter email: ").strip()
    
    # Check if user exists
    if User.objects.filter(phone=phone).exists():
        print(f"❌ User with phone {phone} already exists!")
        return False
    
    if User.objects.filter(email=email).exists():
        print(f"❌ User with email {email} already exists!")
        return False
    
    # Confirm
    print("\n" + "-"*60)
    print(f"Creating Super Admin:")
    print(f"  Phone: {phone}")
    print(f"  Name: {first_name} {last_name}")
    print(f"  Email: {email}")
    print("-"*60)
    
    confirm = input("Confirm creation? (yes/no): ").lower().strip()
    if confirm != "yes":
        print("❌ Creation cancelled")
        return False
    
    # Get password
    password = getpass.getpass("Enter password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    
    if password != password_confirm:
        print("❌ Passwords don't match!")
        return False
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters!")
        return False
    
    # Create user
    try:
        user = User.objects.create_user(
            phone=phone,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_super_admin=True,
            is_active=True
        )
        print(f"\n✅ Super Admin created successfully!")
        print(f"   User ID: {user.id}")
        print(f"   Phone: {user.phone}")
        return True
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        return False

def reset_user_password():
    """Safely reset a user's password"""
    print("\n" + "="*60)
    print("RESET USER PASSWORD")
    print("="*60)
    
    phone = input("Enter user phone number: ").strip()
    
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        print(f"❌ User with phone {phone} not found!")
        return False
    
    print(f"\nResetting password for: {user.get_full_name()} ({user.phone})")
    confirm = input("Confirm? (yes/no): ").lower().strip()
    
    if confirm != "yes":
        print("❌ Operation cancelled")
        return False
    
    # Get new password
    password = getpass.getpass("Enter new password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    
    if password != password_confirm:
        print("❌ Passwords don't match!")
        return False
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters!")
        return False
    
    try:
        user.set_password(password)
        user.save()
        print(f"✅ Password reset successfully for {user.phone}!")
        return True
    except Exception as e:
        print(f"❌ Failed to reset password: {e}")
        return False

def list_super_admins():
    """List all Super Admin users"""
    print("\n" + "="*60)
    print("SUPER ADMINS")
    print("="*60)
    
    super_admins = User.objects.filter(is_super_admin=True)
    
    if not super_admins.exists():
        print("⚠️  No Super Admins found!")
        return
    
    for admin in super_admins:
        status = "✅ ACTIVE" if admin.is_active else "❌ INACTIVE"
        print(f"\n{status}")
        print(f"  ID: {admin.id}")
        print(f"  Name: {admin.get_full_name()}")
        print(f"  Phone: {admin.phone}")
        print(f"  Email: {admin.email}")
        print(f"  Joined: {admin.date_joined.strftime('%Y-%m-%d %H:%M')}")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    while True:
        print("\nUSER MANAGEMENT MENU")
        print("-" * 40)
        print("1. Create Super Admin")
        print("2. Reset User Password")
        print("3. List Super Admins")
        print("4. Exit")
        print("-" * 40)
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == "1":
            create_super_admin()
        elif choice == "2":
            reset_user_password()
        elif choice == "3":
            list_super_admins()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid option!")
