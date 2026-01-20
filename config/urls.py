"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.views import APIView
from rest_framework.response import Response

class HealthCheckView(APIView):
    """Simple health check endpoint."""
    authentication_classes = []
    permission_classes = []
    
    def get(self, request):
        return Response({"status": "ok", "message": "Backend is running"})

class RootView(APIView):
    """Root API endpoint."""
    permission_classes = []
    
    def get(self, request):
        return Response({
            "status": "ok",
            "message": "Billing Application API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health/",
                "auth": "/auth/",
                "users": "/users/",
                "products": "/product/",
                "inventory": "/inventory/",
                "customers": "/customers/",
                "billing": "/billing/",
                "payments": "/payments/",
                "reports": "/reports/",
                "dashboard": "/dashboard/",
            }
        })

urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    # path('admin/', admin.site.urls),
    path('api/auth/', include('apps.auth_app.urls')),
    path("api/users/", include("apps.users.urls")),
    path("api/product/", include("apps.product.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/purchase/", include("apps.purchase.urls")),
    path("api/customers/", include("apps.customer.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/payments/", include("apps.payment.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/common/", include("apps.common.urls")),
    path("api/super-admin/", include("apps.super_admin.urls")),
    path('api/support/', include('apps.support.urls')),
    path("api/subscription/", include("apps.subscription.urls")),
]
