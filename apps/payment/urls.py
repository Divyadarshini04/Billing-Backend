from django.urls import path
from .views import (
    PaymentMethodListView,
    PaymentListCreateView,
    PaymentDetailView,
    PaymentRefundListCreateView,
    PaymentProcessView,
    PaymentCompleteView
)

urlpatterns = [
    # Payment methods
    path('methods/', PaymentMethodListView.as_view(), name='payment-methods'),
    
    # Payments
    path('', PaymentListCreateView.as_view(), name='payment-list'),
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('process/', PaymentProcessView.as_view(), name='payment-process'),
    path('<int:payment_id>/complete/', PaymentCompleteView.as_view(), name='payment-complete'),
    
    # Refunds
    path('refunds/', PaymentRefundListCreateView.as_view(), name='payment-refund-list'),
]
