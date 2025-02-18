# documents/services/notification_service.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


class NotificationService:
    """Handles document-related notifications."""

    @staticmethod
    def send_verification_notification(document, recipient_email, status):
        """Send document verification notification."""
        try:
            context = {
                'document_type': document.get_document_type_display(),
                'verification_status': status,
                'application_number': document.application.application_number,
                'business_name': document.application.business_name,
            }

            # Select template based on status
            if status == 'accepted':
                template_name = 'verification_success'
            elif status == 'rejected':
                template_name = 'verification_failed'
            else:
                template_name = 'verification_review'

            # Render email templates
            html_message = render_to_string(
                f'notifications/email/{template_name}.html',
                context
            )
            text_message = render_to_string(
                f'notifications/email/{template_name}.txt',
                context
            )

            # Send email
            send_mail(
                subject=f'Document Verification {status.title()}',
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message
            )

            return True

        except Exception as e:
            print(f"Notification Error: {str(e)}")
            return False