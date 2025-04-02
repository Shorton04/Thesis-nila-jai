# notifications/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from applications.models import ApplicationRevision, ApplicationAssessment
from django.utils import timezone
from documents.models import Document
from notifications.services.email_service import EmailService
from .models import Notification
from .utils import create_notification
from .utils import send_application_notification
from django.http import HttpResponse
from applications.models import BusinessApplication

@login_required
def test_application_email(request, application_id):
    """Test view to send an application status email"""
    try:
        application = BusinessApplication.objects.get(id=application_id)
        success = send_application_notification(
            request=request,
            user=request.user,
            application=application,
            status=application.status,
            message="This is a test email for application status update."
        )
        if success:
            return HttpResponse(f"Test email sent successfully to {request.user.email}")
        else:
            return HttpResponse("Failed to send test email. Check logs for details.")
    except BusinessApplication.DoesNotExist:
        return HttpResponse("Application not found")


def send_application_notification(user, application, status, message=None):
    """
    Send email notification about application status update
    """
    context = {
        'application': application,
        'user': user,
        'site_url': settings.SITE_URL,
        'message': message,
    }

    # Add additional context based on status
    if status == 'requires_revision':
        # Get latest revision
        revision = ApplicationRevision.objects.filter(
            application=application,
            is_resolved=False
        ).order_by('-requested_date').first()
        context['revision'] = revision

    elif status == 'approved':
        # Get assessment if exists
        assessment = ApplicationAssessment.objects.filter(
            application=application,
            is_paid=False
        ).order_by('-assessment_date').first()
        context['assessment'] = assessment

    # Render email templates
    html_message = render_to_string('notifications/email/application_status_update.html', context)
    text_message = render_to_string('notifications/email/application_status_update.txt', context)

    # Send email
    subject = f"Business Permit Application Update - {application.application_number}"

    send_mail(
        subject,
        text_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

    # Also create a notification in the system
    create_notification(
        user=user,
        title=f"Application Status: {application.get_status_display()}",
        message=message or f"Your application #{application.application_number} status has been updated to {application.get_status_display()}.",
        notification_type='application',
        link=reverse('applications:application_detail', kwargs={'application_id': application.id})
    )

    return True

def approve_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    document.status = 'approved'
    document.save()

    # Send email notification
    EmailService.send_verification_success(
        user=document.application.user,
        document_name=document.name
    )

    return redirect('document_detail', document_id=document_id)

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