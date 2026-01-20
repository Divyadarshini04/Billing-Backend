from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta, datetime
from .models import OTP
from .serializers import SendOTPSerializer, VerifyOTPSerializer, UserMinimalSerializer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import jwt
import logging

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit')

User = get_user_model()

OTP_EXPIRY_MINUTES = getattr(settings, "OTP_EXPIRES_MINUTES", 5)
RATE_LIMIT_KEY = "otp_rate_{phone}"
RATE_LIMIT_WINDOW = 60 * 60  # 1 hour in seconds
MAX_OTP_PER_HOUR = getattr(settings, "OTP_MAX_PER_HOUR", 5)

@method_decorator(csrf_exempt, name='dispatch')
class SendOTP(APIView):
    """Send OTP to phone number with rate limiting and old OTP cleanup."""
    authentication_classes = []  # Disable authentication
    permission_classes = [AllowAny]  # Allow unauthenticated access
    
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        # Rate limiting: cache-based per-phone throttle
        cache_key = RATE_LIMIT_KEY.format(phone=phone)
        counter = cache.get(cache_key, 0)
        if counter >= MAX_OTP_PER_HOUR:
            logger.warning(f"OTP rate limit exceeded for phone: {phone}")
            return Response(
                {"detail": "Rate limit exceeded. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        cache.set(cache_key, counter + 1, RATE_LIMIT_WINDOW)

        # Check if user is deactivated
        try:
            user = User.objects.get(phone=phone)
            if not user.is_active:
                 return Response(
                    {"detail": "Your account is deactivated. Please contact the admin."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except User.DoesNotExist:
            pass # Continue for new users

        # Clean up old OTPs from database (expired/used)
        OTP.delete_old()

        # Invalidate ALL previous active OTPs for this phone number
        # This ensures only the latest OTP is valid
        now = timezone.now()
        existing_active_otps = OTP.objects.filter(
            phone=phone, 
            used=False, 
            expires_at__gt=now
        )
        if existing_active_otps.exists():
            count = existing_active_otps.update(expires_at=now)
            logger.info(f"Invalidated {count} previous OTPs for phone {phone}")

        # Create new OTP using secure manager
        otp = OTP.objects.create_otp(phone=phone, expires_minutes=OTP_EXPIRY_MINUTES)

        # Log OTP send attempt
        audit_logger.info(f"OTP send request: phone={phone}")

        # PRODUCTION: Send OTP via SMS provider (Twilio, AWS SNS, etc.)
        # Example:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=f"Your OTP is: {otp.code}",
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone
        # )

        # DEV ONLY: Return OTP in response (DEBUG mode only)
        if getattr(settings, "DEBUG", False):
            return Response(
                {"detail": "OTP sent", "phone": phone, "otp": otp.code},
                status=status.HTTP_201_CREATED
            )
        
        # PRODUCTION: Return only success message without OTP
        return Response(
            {"detail": "OTP sent successfully"},
            status=status.HTTP_201_CREATED
        )

@method_decorator(csrf_exempt, name='dispatch')
class VerifyOTP(APIView):
    """Verify OTP with expiry check, atomic mark-used, brute-force protection, and user status validation."""
    authentication_classes = []  # Disable authentication
    permission_classes = [AllowAny]  # Allow unauthenticated access
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        # Check brute-force attempt limit
        verify_attempts_key = f"otp_verify_attempts_{phone}_{code}"
        verify_lock_key = f"otp_verify_lock_{phone}_{code}"
        
        if cache.get(verify_lock_key):
            return Response(
                {"detail": "Too many failed attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        max_attempts = getattr(settings, "OTP_MAX_VERIFY_ATTEMPTS", 5)
        verify_attempts = cache.get(verify_attempts_key, 0)
        
        if verify_attempts >= max_attempts:
            lock_duration = getattr(settings, "OTP_LOCK_DURATION_SECONDS", 300)
            cache.set(verify_lock_key, True, lock_duration)
            return Response(
                {"detail": "Too many failed attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        now = timezone.now()
        try:
            with transaction.atomic():
                # Use select_for_update to prevent race conditions
                otp_obj = OTP.objects.select_for_update().get(
                    phone=phone, code=code, used=False, expires_at__gte=now
                )
                # Atomically mark as used
                otp_obj.mark_used()
        except OTP.DoesNotExist:
            # Increment failed attempt counter
            cache.set(verify_attempts_key, verify_attempts + 1, 3600)  # 1 hour window
            logger.warning(f"OTP verification failed: phone={phone}, attempt={verify_attempts + 1}")
            return Response(
                {"detail": "Invalid or expired OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Clear attempt counter on success
        cache.delete(verify_attempts_key)
        cache.delete(verify_lock_key)

        # Get user (DO NOT CREATE)
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found. Please contact your administrator."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check user status
        if not user.is_active:
            logger.warning(f"OTP verification for inactive user: phone={phone}")
            return Response(
                {"detail": "User account is inactive"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Strict Role Validation
        requested_role = request.data.get("role")
        if requested_role:
            has_role = False
            
            if requested_role == "SUPERADMIN":
                if user.is_super_admin or user.user_roles.filter(role__name="SUPERADMIN").exists():
                    has_role = True
            else:
                # Check directly assigned roles
                if user.user_roles.filter(role__name=requested_role).exists():
                    has_role = True
            
            if not has_role:
                logger.warning(f"Role mismatch for user {phone}. Requested: {requested_role}")
                return Response(
                    {"detail": f"Access Denied: You are not authorized as {requested_role}."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Log successful OTP verification
        audit_logger.info(f"OTP verified successfully: phone={phone}, user_id={user.id}")

        # Clean up old OTPs after successful verification
        OTP.delete_old()

        # Generate JWT token with expiry
        payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() + timedelta(seconds=getattr(settings, "JWT_EXPIRY_SECONDS", 86400)),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        # Return user with structured roles
        return Response(
            {
                "detail": "OTP verified successfully",
                "token": token,
                "user": UserMinimalSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )

class LoginView(APIView):
    """Traditional login endpoint for email/phone + password authentication."""
    permission_classes = []  # Allow unauthenticated access
    
    def post(self, request):
        credential = request.data.get("phone") or request.data.get("email")
        password = request.data.get("password")
        
        if not credential or not password:
            return Response(
                {"detail": "Phone/email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find user by phone or email
        user = None
        try:
            user = User.objects.get(phone=credential)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=credential)
            except User.DoesNotExist:
                return Response(
                    {"detail": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Check password
        if not user.check_password(password):
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user is active
        if not user.is_active:
            return Response(
                {"detail": "User account is inactive"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Strict Role Validation
        requested_role = request.data.get("role")
        if requested_role:
            has_role = False
            
            if requested_role == "SUPERADMIN":
                if user.is_super_admin or user.user_roles.filter(role__name="SUPERADMIN").exists():
                    has_role = True
            else:
                # Check directly assigned roles
                if user.user_roles.filter(role__name=requested_role).exists():
                    has_role = True
            
            if not has_role:
                return Response(
                    {"detail": f"Access Denied: You are not authorized as {requested_role}."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Generate JWT token with expiry
        payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() + timedelta(seconds=getattr(settings, "JWT_EXPIRY_SECONDS", 86400)),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        return Response(
            {
                "detail": "Login successful",
                "token": token,
                "user": UserMinimalSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )

class CurrentUserView(APIView):
    """Get current authenticated user information."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserMinimalSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """Handle user logout."""
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)


    