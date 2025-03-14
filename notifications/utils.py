# notifications/utils.py
from .models import Notification
from django.utils import timezone


def create_notification(user, title, message, notification_type='info', link=None):
    """
    Create a new notification for a user

    Args:
        user: The recipient user
        title: Notification title
        message: Notification message
        notification_type: Type of notification (info, success, warning, error, application, document, system)
        link: Optional URL to redirect to when clicked

    Returns:
        The created notification object
    """
    notification = Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        created_at=timezone.now()
    )
    return notification


def send_application_notification(user, application, status, message=None):
    """
    Send a notification about an application status change

    Args:
        user: The recipient user
        application: The BusinessApplication instance
        status: New status of the application
        message: Optional custom message

    Returns:
        The created notification object
    """
    # Set title based on status
    title_map = {
        'submitted': 'Application Submitted',
        'under_review': 'Application Under Review',
        'requires_revision': 'Application Requires Revision',
        'approved': 'Application Approved',
        'rejected': 'Application Rejected',
        'cancelled': 'Application Cancelled',
    }

    title = title_map.get(status, f'Application Status: {status.title()}')

    # Set default message if none provided
    if message is None:
        message_map = {
            'submitted': f'Your application #{application.application_number} has been submitted successfully and is pending review.',
            'under_review': f'Your application #{application.application_number} is now under review.',
            'requires_revision': f'Your application #{application.application_number} requires revision. Please check the details and make the necessary changes.',
            'approved': f'Congratulations! Your application #{application.application_number} has been approved.',
            'rejected': f'Your application #{application.application_number} has been rejected. Please check the details for more information.',
            'cancelled': f'Your application #{application.application_number} has been cancelled.',
        }
        message = message_map.get(status,
                                  f'Your application #{application.application_number} status has been updated to {status.title()}.')

    # Generate link to the application
    from django.urls import reverse
    link = reverse('applications:application_detail', kwargs={'application_id': application.id})

    return create_notification(
        user=user,
        title=title,
        message=message,
        notification_type='application',
        link=link
    )


def send_document_notification(user, document, status, message=None):
    """
    Send a notification about a document status change

    Args:
        user: The recipient user
        document: The Document instance
        status: Status of the document (verified, rejected, etc)
        message: Optional custom message

    Returns:
        The created notification object
    """
    title_map = {
        'verified': 'Document Verified',
        'rejected': 'Document Rejected',
        'quarantined': 'Document Quarantined',
        'submitted': 'Document Submitted',
    }

    title = title_map.get(status, f'Document Status: {status.title()}')

    if message is None:
        message_map = {
            'verified': f'Your document "{document.filename}" has been verified successfully.',
            'rejected': f'Your document "{document.filename}" has been rejected. Please upload a new document.',
            'quarantined': f'Your document "{document.filename}" has been flagged for review. This may delay the processing of your application.',
            'submitted': f'Your document "{document.filename}" has been submitted successfully and is pending review.',
        }
        message = message_map.get(status,
                                  f'Your document "{document.filename}" status has been updated to {status.title()}.')

    # For now, link to the application detail page
    link = None
    if hasattr(document, 'application') and document.application:
        from django.urls import reverse
        link = reverse('applications:application_detail', kwargs={'application_id': document.application.id})

    return create_notification(
        user=user,
        title=title,
        message=message,
        notification_type='document',
        link=link
    )