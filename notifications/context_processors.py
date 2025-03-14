# notifications/context_processors.py
from django.db.models import Count, Q
from .models import Notification


def notification_processor(request):
    context = {
        'has_unread_notifications': False,
        'unread_notifications_count': 0,
        'notifications': []
    }

    if request.user.is_authenticated:
        # Get unread count and recent notifications in a single query
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]

        # Count unread notifications separately to avoid loading all notification objects
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

        context['has_unread_notifications'] = unread_count > 0
        context['unread_notifications_count'] = unread_count
        context['notifications'] = notifications

    return context