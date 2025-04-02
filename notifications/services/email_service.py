# notifications/services/email_service.py

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


class EmailService:
    @staticmethod
    def send_template_email(subject, template_name, context, recipient_list, attachments=None):
        """
        Send an HTML email using a template

        Args:
            subject (str): Email subject
            template_name (str): Path to the template (e.g., 'email/verification_success.html')
            context (dict): Context data for the template
            recipient_list (list): List of email recipients
            attachments (list, optional): List of attachments
        """
        # Render HTML content
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)  # Plain text version

        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list
        )

        # Attach HTML content
        email.attach_alternative(html_content, "text/html")

        # Add attachments if provided
        if attachments:
            for attachment in attachments:
                email.attach(
                    filename=attachment.name,
                    content=attachment.read(),
                    mimetype=attachment.content_type
                )

        # Send email
        return email.send()

    @staticmethod
    def send_verification_success(user, document_name):
        """Send verification success email"""
        subject = "Document Verification Successful"
        template_name = "email/verification_success.html"
        tracking_url = f"{settings.SITE_URL}/applications/tracking/"

        context = {
            'user_name': user.get_full_name() or user.username,
            'document_name': document_name,
            'tracking_url': tracking_url
        }

        recipient_list = [user.email]
        return EmailService.send_template_email(subject, template_name, context, recipient_list)

    # Add more specific email methods as needed
    @staticmethod
    def send_document_rejected(user, document_name, rejection_reason):
        """Send document rejection email"""
        # Implementation similar to send_verification_success
        pass

    @staticmethod
    def send_application_status_update(user, application, new_status):
        """Send application status update email"""
        # Implementation for status updates
        pass