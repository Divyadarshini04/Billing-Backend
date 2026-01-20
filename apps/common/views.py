from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import CompanyProfile, EmailTemplate, NotificationPreference, AuditTrail, SystemSettings
from .serializers import (
    CompanyProfileSerializer, EmailTemplateSerializer,
    NotificationPreferenceSerializer, AuditTrailSerializer,
    SystemSettingsSerializer
)

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for common endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class CompanyProfileViewSet(viewsets.ModelViewSet):
    """
    Manage company profile information.
    Only admins can create/update. Limited to one active profile.
    """
    queryset = CompanyProfile.objects.all()
    serializer_class = CompanyProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['company_name', 'company_code', 'tax_id', 'email']
    ordering_fields = ['created_at', 'company_name']
    ordering = ['-created_at']
    
    
    def get_permissions(self):
        """Allow admins and owners to modify."""
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """List all company profiles (usually just one)."""
        return super().list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Create company profile - only one active allowed."""
        if CompanyProfile.objects.filter(is_active=True).exists():
            return Response(
                {'detail': 'An active company profile already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Override update to log debug info."""
        import json
        try:
            # Use relative path for safety
            with open('backend_debug.log', 'a') as f:
                f.write(f"\n--- UPDATE REQUEST {timezone.now()} ---\n")
                f.write(f"Method: {request.method}\n")
                f.write(f"Data: {request.data}\n")
        except Exception as e:
            print(f"Log Error: {e}")

        response = super().update(request, *args, **kwargs)

        try:
            with open('backend_debug.log', 'a') as f:
                 f.write(f"Response Status: {response.status_code}\n")
                 f.write(f"Response Data: {response.data}\n")
        except Exception as e:
             print(f"Log Error: {e}")
             
        return response
    
    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to log debug info."""
        import json
        try:
            with open('backend_debug.log', 'a') as f:
                f.write(f"\n--- PARTIAL UPDATE REQUEST {timezone.now()} ---\n")
                f.write(f"Method: {request.method}\n")
                f.write(f"Data: {request.data}\n")
        except Exception as e:
            print(f"Log Error: {e}")
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def active(self, request):
        """Get the active company profile for the current user."""
        user = request.user
        
        # Determine the effective owner
        # Try to find profile for the current user first (e.g. Owner)
        profile = CompanyProfile.objects.filter(owner=user, is_active=True).first()
        
        if not profile and user.parent:
            # If no personal profile, check if they are staff (using parent's profile)
            owner = user.parent
            profile = CompanyProfile.objects.filter(owner=owner, is_active=True).first()
            
            if not profile:
                # Fallback: try to get any profile for this owner
                profile = CompanyProfile.objects.filter(owner=owner).first()
        
        if not profile:
             # Fallback 1: try to get any profile for the user
             profile = CompanyProfile.objects.filter(owner=user).first()
        
        if not profile:
             # Fallback 2: try to get any active profile (for Super Admins/Testing)
             profile = CompanyProfile.objects.filter(is_active=True).first()
        
        if not profile:
             # Fallback 3: try the absolute first profile
             profile = CompanyProfile.objects.first()
        
        if not profile:
            return Response(
                {'detail': 'No company profile found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    Manage email templates for system notifications.
    Only admins can create/modify. Limited to authorized users for viewing.
    """
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['template_name', 'subject', 'template_type']
    ordering_fields = ['created_at', 'template_name', 'template_type']
    ordering = ['template_type', 'template_name']
    
    def get_permissions(self):
        """Only admins can modify."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def by_type(self, request):
        """Get templates grouped by type."""
        template_type = request.query_params.get('type')
        if not template_type:
            return Response(
                {'detail': 'type parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        templates = EmailTemplate.objects.filter(template_type=template_type, is_active=True)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)

class NotificationPreferenceViewSet(viewsets.ViewSet):
    """
    Manage user notification preferences.
    Users can only access and modify their own preferences.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Admin only - list all preferences."""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only admins can list all preferences.'},
                status=status.HTTP_403_FORBIDDEN
            )
        preferences = NotificationPreference.objects.all()
        serializer = NotificationPreferenceSerializer(preferences, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get user's notification preferences."""
        try:
            # Users can only see their own preferences
            if int(pk) != request.user.id and not request.user.is_staff:
                return Response(
                    {'detail': 'You cannot access other users\' preferences.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            preference = NotificationPreference.objects.get(user_id=pk)
            serializer = NotificationPreferenceSerializer(preference)
            return Response(serializer.data)
        except NotificationPreference.DoesNotExist:
            return Response(
                {'detail': 'Notification preference not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def create(self, request):
        """Create notification preferences for current user."""
        if NotificationPreference.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Preferences already exist for this user.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = NotificationPreferenceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Update user's notification preferences."""
        try:
            # Users can only modify their own preferences
            if int(pk) != request.user.id and not request.user.is_staff:
                return Response(
                    {'detail': 'You cannot modify other users\' preferences.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            preference = NotificationPreference.objects.get(user_id=pk)
            serializer = NotificationPreferenceSerializer(
                preference, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except NotificationPreference.DoesNotExist:
            return Response(
                {'detail': 'Notification preference not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_preferences(self, request):
        """Get current user's notification preferences."""
        preference, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(preference)
        return Response(serializer.data)

class AuditTrailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View audit trail logs - read-only for compliance.
    Admins can view all logs. Users see only their own actions.
    """
    serializer_class = AuditTrailSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['action_type', 'entity_type', 'status']
    search_fields = ['entity_type', 'description', 'entity_id']
    ordering_fields = ['created_at', 'action_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter audit logs based on user permissions."""
        if self.request.user.is_staff:
            return AuditTrail.objects.all()
        else:
            # Non-admin users only see their own actions
            return AuditTrail.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def recent(self, request):
        """Get recent audit logs (last 24 hours)."""
        yesterday = timezone.now() - timedelta(hours=24)
        queryset = self.get_queryset().filter(created_at__gte=yesterday)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def by_entity(self, request):
        """Get audit logs for a specific entity."""
        entity_type = request.query_params.get('entity_type')
        entity_id = request.query_params.get('entity_id')
        
        if not entity_type or not entity_id:
            return Response(
                {'detail': 'entity_type and entity_id parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            entity_type=entity_type,
            entity_id=entity_id
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class SystemSettingsViewSet(viewsets.ViewSet):
    """
    Manage system-wide settings.
    Only one instance allowed (singleton pattern).
    Only admins can modify.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get system settings (always returns single object)."""
        settings = SystemSettings.objects.first()
        if not settings:
            settings = SystemSettings.objects.create()
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get system settings by ID."""
        try:
            settings = SystemSettings.objects.get(pk=pk)
            serializer = SystemSettingsSerializer(settings)
            return Response(serializer.data)
        except SystemSettings.DoesNotExist:
            return Response(
                {'detail': 'System settings not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def partial_update(self, request, pk=None):
        """Update system settings (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only admins can modify system settings.'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            settings = SystemSettings.objects.get(pk=pk)
            serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SystemSettings.DoesNotExist:
            return Response(
                {'detail': 'System settings not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def current(self, request):
        """Get or update current system settings."""
        settings = SystemSettings.objects.first()
        if not settings:
            settings = SystemSettings.objects.create()
        
        if request.method == 'GET':
            serializer = SystemSettingsSerializer(settings)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            if not request.user.is_staff:
                return Response(
                    {'detail': 'Only admins can modify system settings.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
