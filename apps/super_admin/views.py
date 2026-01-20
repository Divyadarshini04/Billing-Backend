from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from apps.auth_app.permissions import IsSuperAdmin
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.auth_app.models import User
from apps.billing.models import Invoice
from apps.payment.models import Payment
from apps.subscription.models import UserSubscription
from .models import SystemSettings, ActivityLog, Unit
from .serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    SystemSettingsSerializer,
    ActivityLogSerializer,
    UnitSerializer,
)

class DashboardStatsView(APIView):
    """Super Admin Dashboard Statistics"""
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        """Get dashboard statistics for super admin"""
        try:
            # Total users (excluding super admin and staff - only owners)
            total_users = User.objects.filter(is_super_admin=False, parent__isnull=True).count()
            
            # Active owners
            active_owners = User.objects.filter(is_active=True, is_super_admin=False, parent__isnull=True).count()
            
            # Active subscriptions
            active_subscriptions = UserSubscription.objects.filter(status='ACTIVE').count()
            
            # Total revenue (sum of all subscription prices)
            total_revenue = 0
            try:
                subs = UserSubscription.objects.filter(status='ACTIVE')
                for sub in subs:
                    if hasattr(sub.plan, 'price'):
                        total_revenue += float(sub.plan.price)
            except:
                total_revenue = 0
            
            # New signups in last 7 days
            seven_days_ago = timezone.now() - timedelta(days=7)
            new_signups = User.objects.filter(date_joined__gte=seven_days_ago, is_super_admin=False, parent__isnull=True).count()
            
            # Failed payments (unpaid invoices)
            try:
                failed_payments = Invoice.objects.filter(payment_status__in=['unpaid', 'partial']).count()
            except:
                failed_payments = 0
            
            # Expired subscriptions
            expired_subscriptions = UserSubscription.objects.filter(status='EXPIRED').count()
            
            return Response({
                'total_users': total_users,
                'active_owners': active_owners,
                'active_subscriptions': active_subscriptions,
                'total_revenue': int(total_revenue),
                'new_signups': new_signups,
                'failed_payments': failed_payments,
                'expired_subscriptions': expired_subscriptions,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users - Super Admin only"""
    queryset = User.objects.all()
    permission_classes = [IsSuperAdmin]
    serializer_class = UserListSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        elif self.action == "retrieve":
            return UserDetailSerializer
        elif self.action == "retrieve":
            return UserDetailSerializer
        return UserListSerializer

    def perform_create(self, serializer):
        # Users created by Super Admin are independent owners (no parent)
        # Sales Executives are created by Owners and will have a parent set in their respective views
        user = serializer.save(parent=None)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """List all users with pagination and filtering - exclude super admins and staff"""
        queryset = self.get_queryset().filter(is_super_admin=False, parent__isnull=True).order_by("-date_joined")
        
        # Filter by search term
        search = request.query_params.get("search", "")
        if search:
            queryset = queryset.filter(
                phone__icontains=search
            ) | queryset.filter(
                first_name__icontains=search
            ) | queryset.filter(
                last_name__icontains=search
            )

        # Filter by status
        status_filter = request.query_params.get("status")
        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        """Suspend a user account"""
        user = self.get_object()
        user.is_active = False
        user.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action="SUSPEND_USER",
            description=f"Suspended user {user.first_name} {user.last_name} (Phone: {user.phone})",
            ip_address=self.get_client_ip(request),
        )

        return Response(
            {"status": "success", "message": f"User {user.first_name} suspended"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate a user account"""
        user = self.get_object()
        user.is_active = True
        user.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action="ACTIVATE_USER",
            description=f"Activated user {user.first_name} {user.last_name} (Phone: {user.phone})",
            ip_address=self.get_client_ip(request),
        )

        return Response(
            {"status": "success", "message": f"User {user.first_name} activated"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def make_super_admin(self, request, pk=None):
        """Make a user super admin"""
        user = self.get_object()
        user.is_super_admin = True
        user.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE_USER",
            description=f"Made {user.first_name} {user.last_name} a super admin",
            ip_address=self.get_client_ip(request),
        )

        return Response(
            {"status": "success", "message": f"User {user.first_name} is now a super admin"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def revoke_super_admin(self, request, pk=None):
        """Revoke super admin status"""
        user = self.get_object()
        user.is_super_admin = False
        user.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE_USER",
            description=f"Revoked super admin status from {user.first_name} {user.last_name}",
            ip_address=self.get_client_ip(request),
        )

        return Response(
            {"status": "success", "message": f"Super admin status revoked from {user.first_name}"},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        """Delete a user"""
        user = self.get_object()
        user_name = f"{user.first_name} {user.last_name}"

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action="DELETE_USER",
            description=f"Deleted user {user_name} (Phone: {user.phone})",
            ip_address=self.get_client_ip(request),
        )

        user.delete()
        return Response(
            {"status": "success", "message": f"User {user_name} deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=False, methods=["get"])
    def staff_limits(self, request):
        """Get staff limits for current user or specified owner"""
        owner_phone = request.query_params.get('owner_phone')
        
        if owner_phone:
            # Get staff limits for specific owner (Super Admin checking)
            try:
                owner = User.objects.get(phone=owner_phone, is_super_admin=False)
            except User.DoesNotExist:
                return Response(
                    {"error": "Owner not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get staff limits for current user (if they're an owner)
            owner = request.user
            if owner.is_super_admin:
                return Response(
                    {"error": "Super Admin has unlimited staff"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        current_count = owner.get_staff_count()
        max_allowed = owner.get_max_staff_allowed()
        remaining = owner.get_remaining_staff_slots()
        
        # Get subscription info
        subscription = None
        try:
            sub = owner.subscription
            if sub and sub.status == 'ACTIVE':
                subscription = {
                    'plan_name': sub.plan.name,
                    'plan_code': sub.plan.code,
                    'status': sub.status,
                    'end_date': sub.end_date
                }
        except:
            pass
        
        return Response({
            'owner_phone': owner.phone,
            'owner_name': f"{owner.first_name} {owner.last_name}".strip(),
            'current_staff_count': current_count,
            'max_staff_allowed': max_allowed if max_allowed != float('inf') else 'unlimited',
            'remaining_slots': remaining if remaining != float('inf') else 'unlimited',
            'can_create_more': owner.can_create_staff(),
            'subscription': subscription
        })

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        """Reset password for a user - generates new temporary password and sends email"""
        from django.contrib.auth.models import update_session_auth_hash
        import secrets
        
        user = self.get_object()
        
        # Generate temporary password
        temp_password = secrets.token_urlsafe(12)
        user.set_password(temp_password)
        user.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action="RESET_PASSWORD",
            description=f"Reset password for user {user.first_name} {user.last_name} (Phone: {user.phone})",
            ip_address=self.get_client_ip(request),
        )
        
        # TODO: Send email with temporary password
        return Response(
            {
                "status": "success", 
                "message": f"Password reset for {user.first_name}",
                "temp_password": temp_password
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def extend_subscription(self, request, pk=None):
        """Extend a user's subscription by specified days"""
        user = self.get_object()
        days = request.data.get('days', 30)
        
        try:
            subscription = user.subscription
            if not subscription:
                return Response(
                    {"error": "User has no active subscription"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extend end date
            from datetime import timedelta
            new_end_date = subscription.end_date + timedelta(days=days)
            subscription.end_date = new_end_date
            subscription.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action="EXTEND_SUBSCRIPTION",
                description=f"Extended subscription for {user.first_name} {user.last_name} by {days} days (New expiry: {new_end_date.date()})",
                ip_address=self.get_client_ip(request),
            )
            
            return Response(
                {
                    "status": "success",
                    "message": f"Subscription extended by {days} days",
                    "new_expiry": new_end_date
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def change_plan(self, request, pk=None):
        """Change a user's subscription plan"""
        from apps.subscription.models import SubscriptionPlan
        
        user = self.get_object()
        plan_type = request.data.get('plan_type')
        
        if not plan_type:
            return Response(
                {"error": "plan_type is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the plan
            plan = SubscriptionPlan.objects.get(code=plan_type.upper())
            
            subscription = user.subscription
            if not subscription:
                # Create new subscription if doesn't exist
                from datetime import timedelta
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=plan,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=30),
                    status='ACTIVE'
                )
            else:
                # Update existing subscription
                old_plan = subscription.plan.code
                subscription.plan = plan
                subscription.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action="CHANGE_PLAN",
                description=f"Changed subscription plan for {user.first_name} {user.last_name} (Phone: {user.phone}) to {plan_type}",
                ip_address=self.get_client_ip(request),
            )
            
            return Response(
                {
                    "status": "success",
                    "message": f"Plan changed to {plan.name}",
                    "plan_type": plan.code,
                    "plan_name": plan.name
                },
                status=status.HTTP_200_OK,
            )
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": f"Plan {plan_type} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

class SystemSettingsViewSet(viewsets.ViewSet):
    """ViewSet for managing system settings - Super Admin or Owner can manage"""
    
    def get_permissions(self):
        """
        Allow authenticated users to read settings.
        Only Super Admins or Company Owners can update settings.
        """
        if self.request.method in ['PATCH', 'PUT', 'POST', 'DELETE']:
            return [IsAuthenticated()]  # We'll check role in the view
        return [IsAuthenticated()]

    def list(self, request):
        """Get current system settings or handle PATCH requests"""
        # Handle PATCH requests for bulk updates
        if request.method == 'PATCH':
            return self._handle_bulk_update(request)
        
        settings, _ = SystemSettings.objects.get_or_create(pk=1)
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)

    def _handle_bulk_update(self, request):
        """Handle bulk update of settings"""
        try:
            settings = SystemSettings.objects.get(pk=1)
        except SystemSettings.DoesNotExist:
            settings, _ = SystemSettings.objects.get_or_create(pk=1)
        
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action="UPDATE_SETTINGS",
                description="Updated system settings",
                ip_address=self.get_client_ip(request),
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get specific system settings by ID"""
        try:
            settings = SystemSettings.objects.get(pk=pk)
            serializer = SystemSettingsSerializer(settings)
            return Response(serializer.data)
        except SystemSettings.DoesNotExist:
            return Response({"error": "Settings not found"}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        """Update system settings - allows partial updates"""
        try:
            settings = SystemSettings.objects.get(pk=pk)
        except SystemSettings.DoesNotExist:
            settings, _ = SystemSettings.objects.get_or_create(pk=1)
        
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action="UPDATE_SETTINGS",
                description="Updated system settings",
                ip_address=self.get_client_ip(request),
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """Partial update of system settings"""
        try:
            settings = SystemSettings.objects.get(pk=pk)
        except SystemSettings.DoesNotExist:
            settings, _ = SystemSettings.objects.get_or_create(pk=1)
        
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action="UPDATE_SETTINGS",
                description="Updated system settings",
                ip_address=self.get_client_ip(request),
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["patch", "put"], permission_classes=[IsSuperAdmin])
    def bulk_update(self, request):
        """Bulk update settings without ID - for save all controls"""
        # Double-check permission
        if not (request.user and (request.user.is_super_admin or request.user.is_staff)):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            settings = SystemSettings.objects.get(pk=1)
        except SystemSettings.DoesNotExist:
            settings, _ = SystemSettings.objects.get_or_create(pk=1)
        
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action="UPDATE_SETTINGS",
                description="Updated system settings",
                ip_address=self.get_client_ip(request),
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def update_gst_tax(self, request):
        """Update GST percentage"""
        settings, _ = SystemSettings.objects.get_or_create(pk=1)
        
        gst = request.data.get("gst_percentage")

        if gst is not None:
            settings.gst_percentage = gst

        settings.updated_by = request.user
        settings.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE_GST",
            description=f"Updated GST: {gst}%, Tax: {tax}%",
            ip_address=self.get_client_ip(request),
        )

        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing activity logs - Super Admin only"""
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        queryset = ActivityLog.objects.all().order_by("-created_at")

        # Filter by action
        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        # Filter by user
        user_id = self.request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset

class UnitViewSet(viewsets.ModelViewSet):
    """ViewSet for managing units - Super Admin only"""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        """Log unit creation"""
        unit = serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            action="CREATE_UNIT",
            description=f"Created unit: {unit.name} ({unit.symbol})",
            ip_address=self.get_client_ip(self.request),
        )

    def perform_update(self, serializer):
        """Log unit update"""
        unit = serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            action="UPDATE_UNIT",
            description=f"Updated unit: {unit.name} ({unit.symbol})",
            ip_address=self.get_client_ip(self.request),
        )

    def perform_destroy(self, instance):
        """Log unit deletion"""
        ActivityLog.objects.create(
            user=self.request.user,
            action="DELETE_UNIT",
            description=f"Deleted unit: {instance.name}",
            ip_address=self.get_client_ip(self.request),
        )
        instance.delete()

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

class SettingsAPIView(APIView):
    """Direct API endpoint for settings - handles GET and PATCH"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current system settings - accessible to all authenticated users"""
        print(f"DEBUG: Fetching SystemSettings for user {request.user.phone}")
        settings = SystemSettings.objects.first()
        if not settings:
            settings = SystemSettings.objects.create()
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        """Update system settings via PATCH - allow authenticated users to update"""
        import logging
        logger = logging.getLogger('apps')
        
        # Any authenticated user can update system settings
        logger.info(f"DEBUG: Patching SystemSettings for user {request.user.phone}")
        logger.info(f"DEBUG: Payload: {request.data}")
        
        settings = SystemSettings.objects.first()
        if not settings:
            settings = SystemSettings.objects.create()
        
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            settings.refresh_from_db()

            # Sync Free Trial Plan Duration
            try:
                from apps.subscription.models import SubscriptionPlan
                plan = SubscriptionPlan.objects.filter(code="free_trial").first()
                if plan and plan.duration_days != settings.default_trial_days:
                    plan.duration_days = settings.default_trial_days
                    plan.description = f"Free trial for {settings.default_trial_days} days"
                    plan.save()
                    logger.info(f"DEBUG: Synced 'free_trial' plan duration to {settings.default_trial_days}")
            except Exception as e:
                logger.error(f"DEBUG: Error syncing plan duration: {e}")

            # Log activity
            try:
                ActivityLog.objects.create(
                    user=request.user,
                    action="UPDATE_SETTINGS",
                    description="Updated system settings",
                    ip_address=self._get_client_ip(request),
                )
            except Exception as e:
                logger.error(f"Error logging activity: {e}")

            return Response(serializer.data, status=status.HTTP_200_OK)
        
        logger.error(f"DEBUG: Serializer Errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
