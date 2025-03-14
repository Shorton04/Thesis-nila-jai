# notifications/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user)

    # Filter by type if specified
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)

    # Pagination
    paginator = Paginator(notifications, 10)
    page = request.GET.get('page')
    notifications = paginator.get_page(page)

    # Count unread
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'current_type': notification_type
    }
    return render(request, 'notifications/list.html', context)


@login_required
def notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)

    # Mark as read
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    # If there's a link, redirect to it
    if notification.link:
        return redirect(notification.link)

    # Otherwise show the notification detail page
    context = {'notification': notification}
    return render(request, 'notifications/detail.html', context)


@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('notifications:list')


@login_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    messages.success(request, 'Notification deleted successfully.')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('notifications:list')


@login_required
def get_notification_count(request):
    """API endpoint to get unread notification count"""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def get_recent_notifications(request):
    """API endpoint to get recent notifications for the dropdown"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
    results = []

    for notification in notifications:
        results.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message[:50] + '...' if len(notification.message) > 50 else notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'link': notification.link or reverse('notifications:detail', args=[notification.id]),
            'notification_type': notification.notification_type
        })

    return JsonResponse({
        'notifications': results,
        'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count()
    })