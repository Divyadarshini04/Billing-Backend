from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from .models import Ticket, TicketMessage
from .serializers import TicketSerializer, TicketMessageSerializer

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # SUPER ADMIN: Sees only tickets addressed to Super Admin
        if user.is_super_admin:
            return Ticket.objects.filter(level='super_admin').order_by('-updated_at')
        
        # OWNER / SALES EXEC:
        # If user has a parent (Sales Exec), they only see their own tickets (Internal)
        if user.parent:
            return Ticket.objects.filter(user=user).order_by('-updated_at')
            
        # If user has no parent (Owner), they see:
        # 1. Their own tickets (System tickets -> Super Admin)
        # 2. Tickets from their children (Internal tickets -> Owner)
        return Ticket.objects.filter(
            models.Q(user=user) | 
            models.Q(user__parent=user, level='owner')
        ).order_by('-updated_at')

    def perform_create(self, serializer):
        user = self.request.user
        level = 'super_admin' # Default
        
        # Logic:
        # 1. If user has NO parent -> Owner -> Super Admin
        # 2. If user has parent who is Super Admin -> Owner/Direct -> Super Admin
        # 3. If user has parent who is NOT Super Admin -> Staff -> Owner
        
        if user.parent and not user.parent.is_super_admin:
            level = 'owner'
        else:
            level = 'super_admin'
            
        ticket = serializer.save(user=user, level=level)

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Allow Owner to escalate a ticket to Super Admin"""
        ticket = self.get_object()
        
        # Only Owner can escalate tickets from their staff
        if request.user.parent or ticket.user == request.user:
             return Response({"error": "Invalid escalation request"}, status=status.HTTP_403_FORBIDDEN)
             
        # Verify ticket belongs to one of their staff
        if ticket.user.parent != request.user:
            return Response({"error": "You can only escalate tickets from your staff"}, status=status.HTTP_403_FORBIDDEN)

        ticket.level = 'super_admin'
        ticket.save()
        
        # Add a system message
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            message="[System]: Ticket escalated to Super Admin"
        )
        
        return Response({"status": "escalated"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(ticket=ticket, sender=request.user)
            
            # Update updated_at timestamp
            ticket.save() 
            
            # Logic for status updates (optional / simplified)
            if request.user.is_super_admin:
                if ticket.status == 'open':
                    ticket.status = 'in_progress'
                    ticket.save()
            else:
                # User replies
                if request.user == ticket.user:
                    # Re-open if resolved
                    if ticket.status == 'resolved':
                        ticket.status = 'in_progress'
                        ticket.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        if not request.user.is_super_admin and request.user.role != 'OWNER':
             # Allow Owner to update status of their staff tickets?
             # For now, stick to Super Admin or Owner for their specific tickets
             pass
        
        # Simplified permission: Only Super Admin or the designated handler
        ticket = self.get_object()
        
        # Check permissions
        can_update = False
        if request.user.is_super_admin:
            can_update = True
        elif ticket.level == 'owner' and request.user == ticket.user.parent:
            can_update = True
        elif request.user == ticket.user: # User can resolve their own ticket?
            # Maybe allowing user to mark as resolved is fine
            if request.data.get('status') == 'resolved':
                can_update = True

        if not can_update:
             return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if new_status in dict(Ticket.STATUS_CHOICES):
            ticket.status = new_status
            ticket.save()
            return Response({"status": "updated", "new_status": new_status})
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

from .serializers import NotificationSerializer
from .models import Notification

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all_read'})
