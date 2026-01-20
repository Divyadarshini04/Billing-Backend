from rest_framework import serializers
from .models import Ticket, TicketMessage
from apps.users.serializers import UserSerializer

class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.CharField(source='sender.role', read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'ticket', 'sender', 'sender_name', 'sender_role', 'message', 'created_at']
        read_only_fields = ['sender', 'ticket']

    def get_sender_name(self, obj):
        if obj.sender.first_name:
            return f"{obj.sender.first_name} {obj.sender.last_name or ''}".strip()
        return obj.sender.phone

class TicketSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'user', 'user_details', 'company_name', 'subject', 'description', 'category', 'priority', 'status', 'level', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['user', 'status', 'level']

    def get_company_name(self, obj):
        user = obj.user
        # Check direct profile (Owner)
        if hasattr(user, 'company_profile') and user.company_profile:
            return user.company_profile.company_name
        # Check parent profile (Staff)
        if user.parent and hasattr(user.parent, 'company_profile') and user.parent.company_profile:
            return user.parent.company_profile.company_name
        return None

from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

