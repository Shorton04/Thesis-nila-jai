# documents/utils/notifications.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from ..models import Document


class QuarantineNotifier:
    @staticmethod
    def notify_quarantine(document):
        """Send notification when document is quarantined"""
        # Notify uploader
        context = {
            'document': document,
            'reason': document.get_quarantine_reason_display(),
            'date': document.quarantine_date,
            'notes': document.quarantine_notes
        }

        # Email to document uploader
        send_mail(
            subject='Document Quarantined - Action Required',
            message=render_to_string('documents/email/document_quarantined.txt', context),
            html_message=render_to_string('documents/email/document_quarantined.html', context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[document.uploaded_by.email],
            fail_silently=True
        )

        # Notify admins
        admin_context = {
            **context,
            'uploader': document.uploaded_by
        }

        send_mail(
            subject='New Document in Quarantine',
            message=render_to_string('documents/email/admin_quarantine_notification.txt', admin_context),
            html_message=render_to_string('documents/email/admin_quarantine_notification.html', admin_context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email for name, email in settings.ADMINS],
            fail_silently=True
        )

    @staticmethod
    def notify_release(document):
        """Send notification when document is released"""
        context = {
            'document': document,
            'release_date': document.release_date,
            'released_by': document.released_by
        }

        send_mail(
            subject='Document Released from Quarantine',
            message=render_to_string('documents/email/document_released.txt', context),
            html_message=render_to_string('documents/email/document_released.html', context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[document.uploaded_by.email],
            fail_silently=True
        )