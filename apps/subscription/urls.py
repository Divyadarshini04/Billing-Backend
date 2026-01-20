from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionPlanViewSet, UserSubscriptionViewSet

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plans')
router.register(r'subscriptions', UserSubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
    # Custom endpoints for subscription
    path('my-subscription/', UserSubscriptionViewSet.as_view({
        'get': 'my_subscription'
    }), name='my-subscription'),
    path('upgrade/', UserSubscriptionViewSet.as_view({
        'post': 'upgrade'
    }), name='subscription-upgrade'),
    path('cancel/', UserSubscriptionViewSet.as_view({
        'post': 'cancel'
    }), name='subscription-cancel'),
]
