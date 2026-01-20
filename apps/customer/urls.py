from django.urls import path
from .views import (
    CustomerListCreateView,
    CustomerDetailView,
    CustomerAddressListCreateView,
    CustomerAddressDetailView,
    LoyaltyTransactionListView,
    LoyaltySettingsView
)

urlpatterns = [
    # Customer endpoints
    path('', CustomerListCreateView.as_view(), name='customer-list'),
    path('<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    
    # Address endpoints
    path('<int:customer_id>/addresses/', CustomerAddressListCreateView.as_view(), name='customer-address-list'),
    path('addresses/<int:pk>/', CustomerAddressDetailView.as_view(), name='customer-address-detail'),
    
    # Loyalty transactions
    # Loyalty transactions
    path('loyalty/transactions/', LoyaltyTransactionListView.as_view(), name='loyalty-transactions'),
    
    # Loyalty Settings
    path('loyalty/settings/', LoyaltySettingsView.as_view(), name='loyalty-settings'),
]
