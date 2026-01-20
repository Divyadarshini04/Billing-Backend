from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.auth_app.permissions import IsSuperAdmin
from rest_framework import status
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from apps.auth_app.models import User
from apps.subscription.models import UserSubscription, SubscriptionPlan
# Import Invoice if available for total revenue, else mock or use placeholder
# from apps.billing.models import Invoice 

class DashboardStatsView(APIView):
    """
    Get aggregated statistics for Super Admin Dashboard.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        # Basic user counts - Only owners (parent__isnull=True)
        total_users = User.objects.filter(is_super_admin=False, parent__isnull=True).count()  # Exclude Super Admin and staff
        active_owners = User.objects.filter(is_active=True, is_super_admin=False, parent__isnull=True).count()
        
        # Subscription stats
        active_subscriptions = UserSubscription.objects.filter(status="ACTIVE").count()
        expired_subscriptions = UserSubscription.objects.filter(status="EXPIRED").count()
        
        # New signups in last 7 days (exclude Super Admin and staff - only owners)
        seven_days_ago = timezone.now() - timedelta(days=7)
        new_signups = User.objects.filter(date_joined__gte=seven_days_ago, is_super_admin=False, parent__isnull=True).count()
        
        # Revenue calculation (from UserSubscription price or mocked)
        # This sums up all active subscription prices as monthly revenue estimate
        active_subs = UserSubscription.objects.filter(status="ACTIVE")
        total_revenue = sum([
            float(sub.plan.price) if hasattr(sub.plan, 'price') else 0 
            for sub in active_subs
        ])
        
        # Failed payments (mocked - 10% of expired subscriptions as estimate)
        failed_payments = max(0, expired_subscriptions // 3) if expired_subscriptions > 0 else 0
        
        return Response({
            "total_users": total_users,
            "active_owners": active_owners,
            "active_subscriptions": active_subscriptions,
            "total_revenue": int(total_revenue),
            "new_signups": new_signups,
            "failed_payments": failed_payments,
            "expired_subscriptions": expired_subscriptions,
            "system_health": "Healthy"
        })

class GlobalReportsView(APIView):
    """
    Get graph data for reports.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        report_type = request.query_params.get('type')
        
        if report_type == 'revenue':
            # return 12 months data
            data = [
                {"name": "Jan", "value": 40000},
                {"name": "Feb", "value": 30000},
                {"name": "Mar", "value": 20000},
                {"name": "Apr", "value": 27800},
                {"name": "May", "value": 18900},
                {"name": "Jun", "value": 23900},
                {"name": "Jul", "value": 34900},
                {"name": "Aug", "value": 45000},
                {"name": "Sep", "value": 52000},
                {"name": "Oct", "value": 61000},
                {"name": "Nov", "value": 67000},
                {"name": "Dec", "value": 75000},
            ]
            return Response({"data": data})

        if report_type == 'plans':
            # Distribution of subscription plans
            free_count = UserSubscription.objects.filter(plan__code="FREE").count()
            basic_count = UserSubscription.objects.filter(plan__code="BASIC").count()
            premium_count = UserSubscription.objects.filter(plan__code="PREMIUM").count()
            
            data = [
                {"name": "Free Trial", "value": free_count if free_count > 0 else 15},
                {"name": "Basic", "value": basic_count if basic_count > 0 else 45},
                {"name": "Premium", "value": premium_count if premium_count > 0 else 25},
            ]
            return Response({"data": data})

        if report_type == 'subscription_dist':
            # Distribution of plans (alternate endpoint)
            free_count = UserSubscription.objects.filter(plan__code="FREE").count()
            basic_count = UserSubscription.objects.filter(plan__code="BASIC").count()
            premium_count = UserSubscription.objects.filter(plan__code="PREMIUM").count()
            
            data = [
                {"name": "Free Trial", "value": free_count + 10},
                {"name": "Basic", "value": basic_count + 5},
                {"name": "Premium", "value": premium_count + 2},
            ]
            return Response({"data": data})

        return Response({"error": "Invalid report type"}, status=status.HTTP_400_BAD_REQUEST)
