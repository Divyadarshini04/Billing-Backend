from django.db import models
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager, AbstractUser
import re
from django.core.exceptions import ValidationError
from django.db.models import Q, UniqueConstraint, Index
import secrets
from datetime import timedelta

# More flexible phone validation - allows any 10-digit number for development
PHONE_REGEX = r'^[0-9]{10}$'

def validate_indian_phone(value):
    if not re.match(PHONE_REGEX, value):
        raise ValidationError("Please enter a valid 10-digit phone number")

# -----------------------------
# OTP MANAGER (Secure Generation)
# -----------------------------
class OTPManager(models.Manager):
    def create_otp(self, phone, length=6, expires_minutes=5):
        """Create OTP using secrets module for secure random generation."""
        code = str(secrets.randbelow(10**length)).zfill(length)
        now = timezone.now()
        otp = self.create(
            phone=phone,
            code=code,
            created_at=now,
            expires_at=now + timedelta(minutes=expires_minutes),
            used=False
        )
        return otp

# -----------------------------
# OTP MODEL
# -----------------------------
class OTP(models.Model):
    phone = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)
    used = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    objects = OTPManager()

    class Meta:
        indexes = [
            Index(fields=["phone", "created_at"]),
            Index(fields=["phone", "used"]),
            Index(fields=["expires_at"]),
        ]
        constraints = [
            UniqueConstraint(
                fields=["phone", "code", "used"],
                name="unique_active_otp",
                condition=Q(used=False)
            )
        ]

    @staticmethod
    def delete_old():
        """Delete expired and used OTPs."""
        now = timezone.now()
        deleted, _ = OTP.objects.filter(
            models.Q(used=True) | models.Q(expires_at__lt=now)
        ).delete()
        return deleted

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_used(self):
        """Mark OTP as used atomically."""
        if not self.used:
            self.used = True
            self.save(update_fields=["used"])

# -----------------------------
# USER MANAGER
# -----------------------------
class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_super_admin", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(phone, password, **extra_fields)

# -----------------------------
# USER MODEL
# -----------------------------
class User(AbstractUser):
    phone = models.CharField(
        max_length=15,
        unique=True,
        validators=[validate_indian_phone]
    )
    username = None  # disable username
    is_super_admin = models.BooleanField(default=False, db_index=True)  # Super Admin flag
    
    # Business Type
    BUSINESS_TYPE_CHOICES = [
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('service', 'Service'),
        ('grocery', 'Grocery'),
    ]
    business_type = models.CharField(
        max_length=20,
        choices=BUSINESS_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Type of business"
    )
    
    # Hierarchy: Super Admin -> Owner -> Sales Executive
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='children',
        help_text="The parent user who created/manages this user (e.g., Owner manages Sales Exec)"
    )

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()  # Correct user manager

    def __str__(self):
        return self.phone

    def get_staff_count(self):
        """Get count of Sales Executive staff created by this Owner"""
        return self.children.filter(parent__isnull=False).count()

    def get_max_staff_allowed(self):
        """Get maximum staff users allowed based on subscription plan. Returns -1 for unlimited."""
        if self.is_super_admin:
            return -1  # Super admin has unlimited
        
        # Get user's subscription plan
        try:
            subscription = self.subscription
            if subscription and subscription.status == 'ACTIVE':
                plan = subscription.plan
                if plan.max_staff_users == 0:
                    return -1  # 0 means unlimited
                return plan.max_staff_users
        except:
            pass
        
        return 1  # Default to 1 if no subscription found

    def can_create_staff(self):
        """Check if user can create more staff (Sales Executives)"""
        current_count = self.get_staff_count()
        max_allowed = self.get_max_staff_allowed()
        if max_allowed == -1:
            return True
        return current_count < max_allowed

    def get_remaining_staff_slots(self):
        """Get remaining staff slots available. Returns -1 for unlimited."""
        max_allowed = self.get_max_staff_allowed()
        if max_allowed == -1:
            return -1
        current_count = self.get_staff_count()
        return max(0, max_allowed - current_count)
