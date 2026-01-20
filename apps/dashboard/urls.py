from django.urls import path
from .views import (
    DashboardOverviewView,
    DashboardAnalyticsView,
    TopProductsView,
    RecentTransactionsView,
    LowStockAlertsView,
    ComprehensiveAnalyticsView
)

urlpatterns = [
    path('overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('comprehensive-analytics/', ComprehensiveAnalyticsView.as_view(), name='comprehensive-analytics'),
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('recent/', RecentTransactionsView.as_view(), name='recent-transactions'),
    path('low-stock/', LowStockAlertsView.as_view(), name='low-stock-alerts'),
]
