"""
Tests for auth_app module covering OTP, JWT, rate limiting, and authentication.
"""

from django.test import TestCase, Client
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta, datetime
import json
from .models import OTP, User
from .serializers import SendOTPSerializer, VerifyOTPSerializer

class OTPManagerTests(TestCase):
    """Test OTP creation and management."""
    
    def setUp(self):
        self.phone = '9876543210'
        cache.clear()
    
    def test_create_otp_generates_valid_code(self):
        """Test OTP creation generates a 6-digit code."""
        otp = OTP.objects.create_otp(phone=self.phone)
        self.assertEqual(len(otp.code), 6)
        self.assertTrue(otp.code.isdigit())
        self.assertFalse(otp.used)
    
    def test_otp_expiry_timestamp(self):
        """Test OTP expires_at is set correctly."""
        otp = OTP.objects.create_otp(phone=self.phone, expires_minutes=5)
        expected_expiry = timezone.now() + timedelta(minutes=5)
        # Allow 2-second tolerance
        self.assertLess(abs((otp.expires_at - expected_expiry).total_seconds()), 2)
    
    def test_delete_old_removes_expired_otps(self):
        """Test delete_old() removes expired OTPs."""
        # Create OTP that will expire
        otp_old = OTP.objects.create(
            phone=self.phone,
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1),
            used=False
        )
        
        # Create fresh OTP
        otp_fresh = OTP.objects.create_otp(phone=self.phone)
        
        # Delete old ones
        deleted_count = OTP.delete_old()
        
        # Old should be deleted, fresh should exist
        self.assertGreater(deleted_count, 0)
        self.assertTrue(OTP.objects.filter(id=otp_fresh.id).exists())
        self.assertFalse(OTP.objects.filter(id=otp_old.id).exists())
    
    def test_mark_used_atomically(self):
        """Test mark_used() sets used flag."""
        otp = OTP.objects.create_otp(phone=self.phone)
        self.assertFalse(otp.used)
        
        otp.mark_used()
        otp.refresh_from_db()
        self.assertTrue(otp.used)
    
    def test_is_expired_returns_true_for_old_otp(self):
        """Test is_expired() correctly identifies expired OTPs."""
        otp = OTP.objects.create(
            phone=self.phone,
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1),
            used=False
        )
        self.assertTrue(otp.is_expired())

class SendOTPTests(TestCase):
    """Test SendOTP view and rate limiting."""
    
    def setUp(self):
        self.client = Client()
        self.url = '/api/auth/send-otp/'  # Adjust based on actual URL
        self.phone = '9876543210'
        cache.clear()
    
    def test_send_otp_with_valid_phone(self):
        """Test successful OTP sending."""
        response = self.client.post(
            self.url,
            {'phone': self.phone},
            content_type='application/json'
        )
        self.assertIn(response.status_code, [201, 200])
        
        # Verify OTP was created
        otp = OTP.objects.filter(phone=self.phone).first()
        self.assertIsNotNone(otp)
    
    def test_send_otp_with_invalid_phone(self):
        """Test OTP sending with invalid phone number."""
        invalid_phones = ['123', '98765', '12345678901']  # Too short, too long, invalid format
        
        for phone in invalid_phones:
            response = self.client.post(
                self.url,
                {'phone': phone},
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 400)
    
    def test_rate_limiting_on_send_otp(self):
        """Test rate limiting prevents excessive OTP requests."""
        # Send OTPs up to limit
        max_per_hour = 5
        for i in range(max_per_hour):
            response = self.client.post(
                self.url,
                {'phone': self.phone},
                content_type='application/json'
            )
            self.assertNotEqual(response.status_code, 429)
        
        # Next request should be rate limited
        response = self.client.post(
            self.url,
            {'phone': self.phone},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 429)

class VerifyOTPTests(TestCase):
    """Test VerifyOTP view, user creation, JWT generation, and brute-force protection."""
    
    def setUp(self):
        self.client = Client()
        self.verify_url = '/api/auth/verify-otp/'  # Adjust based on actual URL
        self.phone = '9876543210'
        cache.clear()
    
    def test_verify_otp_creates_jwt_with_expiry(self):
        """Test successful OTP verification and JWT token generation with expiry."""
        # Create OTP
        otp = OTP.objects.create_otp(phone=self.phone)
        
        # Verify OTP
        response = self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': otp.code},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())
        
        # Token should have exp claim
        import jwt
        from django.conf import settings
        token = response.json()['token']
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        self.assertIn('exp', payload)
        self.assertIn('user_id', payload)
        self.assertIn('iat', payload)
    
    def test_verify_otp_creates_user(self):
        """Test OTP verification creates user if not exists."""
        otp = OTP.objects.create_otp(phone=self.phone)
        
        # Should not exist yet
        self.assertFalse(User.objects.filter(phone=self.phone).exists())
        
        # Verify OTP
        response = self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': otp.code},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # User should now exist
        user = User.objects.get(phone=self.phone)
        self.assertTrue(user.is_active)
    
    def test_verify_otp_rejects_expired_otp(self):
        """Test OTP verification fails for expired OTPs."""
        # Create expired OTP
        otp = OTP.objects.create(
            phone=self.phone,
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1),
            used=False
        )
        
        response = self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': '123456'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_verify_otp_rejects_used_otp(self):
        """Test OTP verification fails for already used OTPs."""
        otp = OTP.objects.create_otp(phone=self.phone)
        otp.mark_used()
        
        response = self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': otp.code},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_brute_force_protection_locks_after_failed_attempts(self):
        """Test brute-force protection locks account after failed attempts."""
        # Create OTP
        otp = OTP.objects.create_otp(phone=self.phone)
        
        # Make 5 failed attempts
        for i in range(5):
            response = self.client.post(
                self.verify_url,
                {'phone': self.phone, 'code': 'wrong_code'},
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 400)
        
        # Next attempt should be locked (rate limited)
        response = self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': 'wrong_code'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 429)
    
    def test_verify_otp_clears_attempt_counter_on_success(self):
        """Test failed attempt counter is cleared after successful verification."""
        # Create OTP
        otp = OTP.objects.create_otp(phone=self.phone)
        
        # Make one failed attempt
        self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': 'wrong_code'},
            content_type='application/json'
        )
        
        # Verify with correct code should succeed
        response = self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': otp.code},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_verify_otp_rejects_inactive_user(self):
        """Test OTP verification fails for inactive users."""
        # Create user and make inactive
        user = User.objects.create(phone=self.phone, is_active=False)
        otp = OTP.objects.create_otp(phone=self.phone)
        
        response = self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': otp.code},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_verify_otp_marks_used(self):
        """Test OTP is marked as used after verification."""
        otp = OTP.objects.create_otp(phone=self.phone)
        
        self.client.post(
            self.verify_url,
            {'phone': self.phone, 'code': otp.code},
            content_type='application/json'
        )
        
        otp.refresh_from_db()
        self.assertTrue(otp.used)

class LoginViewTests(TestCase):
    """Test traditional login endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.login_url = '/api/auth/login/'  # Adjust based on actual URL
        self.phone = '9876543210'
        self.password = 'test_password_123'
        
        # Create test user
        self.user = User.objects.create_user(
            phone=self.phone,
            password=self.password,
            email='test@example.com'
        )
    
    def test_login_with_valid_credentials(self):
        """Test successful login."""
        response = self.client.post(
            self.login_url,
            {'username': self.phone, 'password': self.password},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())
    
    def test_login_with_email(self):
        """Test login using email instead of phone."""
        response = self.client.post(
            self.login_url,
            {'username': self.user.email, 'password': self.password},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_login_with_invalid_password(self):
        """Test login fails with incorrect password."""
        response = self.client.post(
            self.login_url,
            {'username': self.phone, 'password': 'wrong_password'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_login_with_nonexistent_user(self):
        """Test login fails for non-existent user."""
        response = self.client.post(
            self.login_url,
            {'username': '9999999999', 'password': self.password},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_login_returns_jwt_with_expiry(self):
        """Test login returns JWT with expiry."""
        response = self.client.post(
            self.login_url,
            {'username': self.phone, 'password': self.password},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        import jwt
        from django.conf import settings
        token = response.json()['token']
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        self.assertIn('exp', payload)
        self.assertIn('user_id', payload)
    
    def test_login_fails_for_inactive_user(self):
        """Test login fails for inactive user."""
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post(
            self.login_url,
            {'username': self.phone, 'password': self.password},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)

class SerializerValidationTests(TestCase):
    """Test serializer validation for OTP endpoints."""
    
    def test_send_otp_serializer_validates_phone(self):
        """Test SendOTPSerializer validates phone format."""
        serializer = SendOTPSerializer(data={'phone': 'invalid'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)
    
    def test_verify_otp_serializer_validates_code(self):
        """Test VerifyOTPSerializer validates OTP code."""
        serializer = VerifyOTPSerializer(data={'phone': '9876543210', 'code': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('code', serializer.errors)

