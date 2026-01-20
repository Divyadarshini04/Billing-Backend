from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SendOTP,
    VerifyOTP,
    LoginView,
    CurrentUserView,
    LogoutView,
    OTPLoginView
)

urlpatterns = [
    path("send-otp/", SendOTP.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTP.as_view(), name="verify-otp"),

    # PASSWORD LOGIN (SUPER ADMIN / STAFF)
    path("login/", LoginView.as_view(), name="login"),

    # OTP LOGIN (OWNER)
    path("otp-login/", OTPLoginView.as_view(), name="otp-login"),

    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("user/", CurrentUserView.as_view(), name="current-user"),
    path("logout/", LogoutView.as_view(), name="logout"),
]

    
