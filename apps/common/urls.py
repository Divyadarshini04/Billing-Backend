from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyProfileViewSet, EmailTemplateViewSet,
    NotificationPreferenceViewSet, AuditTrailViewSet,
    SystemSettingsViewSet
)

router = DefaultRouter()
router.register(r'company', CompanyProfileViewSet, basename='company-profile')
router.register(r'email-templates', EmailTemplateViewSet, basename='email-template')
router.register(r'notifications', NotificationPreferenceViewSet, basename='notification-preference')
router.register(r'audit', AuditTrailViewSet, basename='audit-trail')
router.register(r'settings', SystemSettingsViewSet, basename='system-settings')

urlpatterns = [
    path('', include(router.urls)),
]
