"""
Custom JWT Authentication for DRF using existing JWT token format.
"""

import jwt
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)
User = get_user_model()

class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT authentication that decodes tokens and sets user on request.
    Works with existing custom JWT token generation.
    """
    keyword = 'Bearer'

    def get_authorization_header(self, request):
        """
        Return request headers as a string.
        """
        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(auth, str):
            # Work around django test client oddness
            auth = auth.encode(encoding='utf-8')
        return auth

    def authenticate(self, request):
        """
        Authenticate the request using JWT token from Authorization header.
        """
        auth = self.get_authorization_header(request).split()

        # No auth header
        if not auth:
            logger.debug("JWTAuth: No Authorization header found.")
            return None

        logger.debug(f"JWTAuth: Authorization Header received: {[x.decode('utf-8') for x in auth]}")

        # Check keyword (Bearer)
        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise AuthenticationFailed(msg)

        if len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise AuthenticationFailed(msg)

        keyword = auth[0].decode('utf-8')
        token = auth[1].decode('utf-8')

        # Check keyword matches
        if keyword.lower() != self.keyword.lower():
            logger.debug(f"JWTAuth: Keyword mismatch. Expected {self.keyword}, got {keyword}")
            return None

        # Decode token
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            msg = 'Token has expired.'
            raise AuthenticationFailed(msg)
        except jwt.InvalidTokenError:
            msg = 'Invalid token.'
            raise AuthenticationFailed(msg)

        # Get user from payload
        user_id = payload.get('user_id')
        if not user_id:
            msg = 'Token contains no user_id.'
            raise AuthenticationFailed(msg)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            msg = 'User not found.'
            raise AuthenticationFailed(msg)

        # Check user is active
        if not user.is_active:
            msg = 'User inactive or deleted.'
            raise AuthenticationFailed(msg)

        logger.debug(f"JWT authentication successful for user: {user.id}")
        return (user, token)
