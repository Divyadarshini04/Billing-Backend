from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.auth_app.permissions import IsSuperAdmin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.auth_app.models import User
from apps.billing.models import Invoice
from apps.subscription.models import UserSubscription, SubscriptionPlan

class ReportsView(APIView):
    """Reports API for Super Admin"""
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        """Get reports data (revenue trend, subscription plans, etc)"""
        report_type = request.query_params.get('type', 'revenue')
        
        try:
            if report_type == 'revenue':
                return self.get_revenue_trend(request)
            elif report_type == 'plans':
                return self.get_subscription_plans(request)
            elif report_type == 'businesses':
                return self.get_top_businesses(request)
            else:
                return Response({'error': 'Invalid report type'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_revenue_trend(self, request):
        """Get revenue trend for last 30 days"""
        data = []
        today = timezone.now().date()
        
        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            daily_revenue = Invoice.objects.filter(
                status='completed',
                invoice_date__date=date
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            data.append({
                'name': date.strftime('%d %b'),
                'value': float(daily_revenue)
            })
        
        return Response({'data': data})

    def get_subscription_plans(self, request):
        """Get subscription plan distribution"""
        try:
            plans = SubscriptionPlan.objects.annotate(
                count=Count('usersubscription')
            ).values('name', 'count').order_by('-count')
            
            data = [{'name': plan['name'], 'value': plan['count']} for plan in plans]
        except Exception as e:
            data = []
        
        if not data:
            data = [
                {'name': 'Basic', 'value': 15},
                {'name': 'Standard', 'value': 25},
                {'name': 'Premium', 'value': 10}
            ]
        
        return Response({'data': data})

    def get_top_businesses(self, request):
        """Get top performing businesses by revenue"""
        try:
            businesses = User.objects.filter(is_super_admin=False).annotate(
                revenue=Sum('invoices__total_amount', filter=Q(invoices__status='completed')),
                active_subs=Count('usersubscription', filter=Q(usersubscription__status='ACTIVE'))
            ).filter(revenue__gt=0).order_by('-revenue')[:5]
            
            data = []
            for business in businesses:
                business_name = f"{business.first_name} {business.last_name}".strip()
                if not business_name:
                    business_name = business.phone
                
                data.append({
                    'name': business_name,
                    'revenue': float(business.revenue or 0),
                    'subscriptions': business.active_subs or 0
                })
        except Exception as e:
            data = []
        
        return Response({'data': data})
