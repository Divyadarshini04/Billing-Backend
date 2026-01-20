from django.urls import path
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response

class HealthCheckView(APIView):
    """Simple health check endpoint."""
    permission_classes = []
    
    def get(self, request):
        return Response({"status": "ok", "message": "Backend is running"})

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
