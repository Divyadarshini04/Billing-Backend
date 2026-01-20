from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for Subscription Plans"""
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for User Subscriptions"""
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    staff_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = '__all__'
        read_only_fields = ('user', 'start_date', 'end_date', 'status')

    def get_staff_count(self, obj):
        return obj.user.get_staff_count()
