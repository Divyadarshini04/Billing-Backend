from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, UserSubscription
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer

class IsSuperAdmin(permissions.BasePermission):
    """Allow access only to super admins"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_super_admin or request.user.is_superuser)

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """
    CRUD for Subscription Plans.
    - Public: List/Retrieve
    - SuperAdmin: Create/Update/Delete
    """
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsSuperAdmin()]

class UserSubscriptionViewSet(viewsets.ModelViewSet):
    """
    Manage User Subscriptions.
    - Users can view their own subscription.
    - SuperAdmins can manage any subscription.
    """
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_super_admin:
            return UserSubscription.objects.all()
        return UserSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Only Super Admin can manually create a subscription via API
        # (Regular users would go through payment gateway webhook)
        if not self.request.user.is_super_admin:
            raise permissions.PermissionDenied("Only admins can manually assign subscriptions.")
        serializer.save()

    @action(detail=False, methods=['post'])
    def assign_trial(self, request):
        """Assign free trial to the logged-in user if compatible"""
        user = request.user
        if hasattr(user, 'subscription'):
            return Response({"error": "User already has a subscription history"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            free_plan = SubscriptionPlan.objects.get(code="FREE")
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Free plan configuration missing"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        subscription = UserSubscription.objects.create(
            user=user,
            plan=free_plan,
            status="ACTIVE"
        )
        serializer = self.get_serializer(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def auto_upgrade_trials(self, request):
        """
        Auto-upgrade expired Free Trial subscriptions to Basic plan.
        Only accessible by Super Admin.
        """
        if not request.user.is_super_admin:
            return Response(
                {"error": "Only admins can trigger auto-upgrades"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            free_trial_plan = SubscriptionPlan.objects.get(code='FREE')
            basic_plan = SubscriptionPlan.objects.get(code='BASIC')
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "Required subscription plans not found"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Find expired Free Trial subscriptions
        expired_trials = UserSubscription.objects.filter(
            plan=free_trial_plan,
            status='EXPIRED',
            end_date__lte=timezone.now()
        )

        upgraded_count = 0
        upgraded_users = []
        
        for subscription in expired_trials:
            try:
                # Update to Basic subscription
                subscription.plan = basic_plan
                subscription.status = 'ACTIVE'
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=basic_plan.duration_days)
                subscription.auto_renew = False
                subscription.save()

                upgraded_count += 1
                upgraded_users.append({
                    'phone': subscription.user.phone,
                    'name': f"{subscription.user.first_name} {subscription.user.last_name}".strip(),
                    'new_plan': basic_plan.name
                })
            except Exception as e:
                pass

        return Response({
            'message': f'Successfully upgraded {upgraded_count} users from Free Trial to Basic',
            'upgraded_count': upgraded_count,
            'upgraded_users': upgraded_users
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def my_subscription(self, request):
        """Get the current user's active subscription
        - For owners: returns owner's subscription OR any staff member's ACTIVE subscription
        - For staff: returns their own subscription
        """
        user = request.user
        
        try:
            # First, check if the user has their own active subscription
            subscription = UserSubscription.objects.get(user=user, status='ACTIVE')
            serializer = self.get_serializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserSubscription.DoesNotExist:
            # If owner with no active subscription, check if any staff has active subscription
            if user.parent is None:  # User is an owner
                staff_subscriptions = UserSubscription.objects.filter(
                    user__parent=user,
                    status='ACTIVE'
                )
                if staff_subscriptions.exists():
                    subscription = staff_subscriptions.first()
                    serializer = self.get_serializer(subscription)
                    return Response(serializer.data, status=status.HTTP_200_OK)
            
            # No active subscription found for user or their staff
            return Response(
                {"error": "No active subscription found"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def upgrade(self, request):
        """Upgrade or change user's subscription plan"""
        plan_id = request.data.get('plan_id')
        
        if not plan_id:
            return Response(
                {"error": "plan_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "Plan not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Calculate end date based on plan duration
            start_date = timezone.now()
            if plan.duration_days == 0:  # Unlimited
                end_date = timezone.now() + timedelta(days=365*10)  # 10 years as unlimited
            else:
                end_date = start_date + timedelta(days=plan.duration_days)

            try:
                subscription = UserSubscription.objects.get(user=request.user)
                # Update existing subscription
                subscription.plan = plan
                subscription.status = 'ACTIVE'
                subscription.start_date = start_date
                subscription.end_date = end_date
                subscription.auto_renew = False
                subscription.payment_method = request.data.get('payment_method')
                subscription.payment_details = request.data.get('payment_details', {})
                subscription.save()
            except UserSubscription.DoesNotExist:
                # Create new subscription
                subscription = UserSubscription.objects.create(
                    user=request.user,
                    plan=plan,
                    status='ACTIVE',
                    start_date=start_date,
                    end_date=end_date,
                    auto_renew=False,
                    payment_method=request.data.get('payment_method'),
                    payment_details=request.data.get('payment_details', {})
                )
            
            serializer = self.get_serializer(subscription)
            return Response({
                "message": f"Successfully upgraded to {plan.name}",
                "subscription": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Cancel the user's active subscription"""
        try:
            subscription = UserSubscription.objects.get(
                user=request.user, 
                status='ACTIVE'
            )
            subscription.status = 'CANCELLED'
            subscription.auto_renew = False
            subscription.save()
            
            serializer = self.get_serializer(subscription)
            return Response({
                "message": "Subscription cancelled successfully",
                "subscription": serializer.data
            }, status=status.HTTP_200_OK)
            
        except UserSubscription.DoesNotExist:
            return Response(
                {"error": "No active subscription found to cancel"},
                status=status.HTTP_404_NOT_FOUND
            )
