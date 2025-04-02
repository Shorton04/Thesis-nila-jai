# notifications/utils.py
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from applications.models import ApplicationRevision, ApplicationAssessment

logger = logging.getLogger(__name__)


def create_notification(user, title, message, notification_type='info', link=None):
    """
    Create an in-app notification
    """
    # If you have a Notification model, create it here
    from notifications.models import Notification

    try:
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
        return notification
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        return None


def send_application_notification(user, application, status, message=None, request=None):
    """
    Send email notification about application status update
    """
    try:
        # Build absolute URL for the site
        if request and hasattr(request, 'build_absolute_uri'):
            site_url = request.build_absolute_uri('/').rstrip('/')
        else:
            # Fallback to settings if request is not available
            site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'

        context = {
            'application': application,
            'user': user,
            'site_url': site_url,
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

        # Log what we're about to do
        logger.info(f"Sending status update email to {user.email} for application {application.application_number}")

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

        logger.info(f"Email sent successfully to {user.email}")

        # Also create a notification in the system
        notification_message = message or f"Your application #{application.application_number} status has been updated to {application.get_status_display()}."
        create_notification(
            user=user,
            title=f"Application Status: {application.get_status_display()}",
            message=notification_message,
            notification_type='application',
            link=reverse('applications:application_detail', kwargs={'application_id': application.id})
        )

        return True
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")
        # Still create the notification even if email fails
        try:
            notification_message = message or f"Your application #{application.application_number} status has been updated to {application.get_status_display()}."
            create_notification(
                user=user,
                title=f"Application Status: {application.get_status_display()}",
                message=notification_message,
                notification_type='application',
                link=reverse('applications:application_detail', kwargs={'application_id': application.id})
            )
        except Exception as inner_e:
            logger.error(f"Failed to create notification: {str(inner_e)}")

        return False


def send_document_notification(request, user, document, status, message=None):
    """
    Send email notification about document status update
    """
    try:
        # Build absolute URL for the site
        if hasattr(request, 'build_absolute_uri'):
            site_url = request.build_absolute_uri('/').rstrip('/')
        else:
            # Fallback to settings if request is not available
            site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'

        context = {
            'document': document,
            'user': user,
            'site_url': site_url,
            'message': message,
            'status': status
        }

        # Log what we're about to do
        logger.info(f"Sending document status update email to {user.email} for document {document.filename}")

        # Render email templates
        html_message = render_to_string('notifications/email/document_status_update.html', context)
        text_message = render_to_string('notifications/email/document_status_update.txt', context)

        # Send email
        subject = f"Document Status Update - {document.filename}"

        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Document email sent successfully to {user.email}")

        # Also create a notification in the system
        notification_message = message or f"Your document '{document.filename}' status has been updated to {status}."
        create_notification(
            user=user,
            title=f"Document Status: {status}",
            message=notification_message,
            notification_type='document',
            link=reverse('applications:application_detail',
                         kwargs={'application_id': document.application.id}) if hasattr(document,
                                                                                        'application') else None
        )

        return True
    except Exception as e:
        logger.error(f"Failed to send document email notification: {str(e)}")
        # Still create the notification even if email fails
        try:
            notification_message = message or f"Your document '{document.filename}' status has been updated to {status}."
            create_notification(
                user=user,
                title=f"Document Status: {status}",
                message=notification_message,
                notification_type='document',
                link=reverse('applications:application_detail',
                             kwargs={'application_id': document.application.id}) if hasattr(document,
                                                                                            'application') else None
            )
        except Exception as inner_e:
            logger.error(f"Failed to create document notification: {str(inner_e)}")

        return False


def send_deadline_reminder(user, application, deadline, revision=None, assessment=None, request=None):
    """
    Send a reminder email about an upcoming deadline
    """
    try:
        # Build absolute URL for the site
        if request and hasattr(request, 'build_absolute_uri'):
            site_url = request.build_absolute_uri('/').rstrip('/')
        else:
            # Fallback to settings if request is not available
            site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'

        context = {
            'application': application,
            'user': user,
            'site_url': site_url,
            'deadline': deadline,
            'revision': revision,
            'assessment': assessment
        }

        # Log what we're about to do
        logger.info(f"Sending deadline reminder email to {user.email} for application {application.application_number}")

        # Render email templates
        html_message = render_to_string('notifications/email/deadline_reminder.html', context)
        text_message = render_to_string('notifications/email/deadline_reminder.txt', context)

        # Send email
        subject = f"REMINDER: Deadline Tomorrow - Application #{application.application_number}"

        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Deadline reminder email sent successfully to {user.email}")

        # Create an in-app notification as well
        if revision:
            notification_message = f"Reminder: Your application revision deadline is tomorrow ({deadline.strftime('%B %d, %Y')})."
        elif assessment:
            notification_message = f"Reminder: Your payment deadline is tomorrow ({deadline.strftime('%B %d, %Y')})."
        else:
            notification_message = f"Reminder: You have an application deadline tomorrow ({deadline.strftime('%B %d, %Y')})."

        create_notification(
            user=user,
            title="Deadline Reminder",
            message=notification_message,
            notification_type='deadline',
            link=reverse('applications:application_detail', kwargs={'application_id': application.id})
        )

        return True
    except Exception as e:
        logger.error(f"Failed to send deadline reminder email: {str(e)}")
        return False