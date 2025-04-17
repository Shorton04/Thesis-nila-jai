from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string


class NotificationService:
    """
    Service for sending notifications about document verification results
    """

    @staticmethod
    def send_document_verified_notification(document):
        """
        Send notification that a document has been verified
        """
        # This would normally call an external notification service
        # or use Django's email functionality
        try:
            # In a production app, you'd send an actual email
            # For demonstration, just log it
            print(f"[NOTIFICATION] Document Verified: {document.id} - {document.get_document_type_display()}")

            # You could add a record to a notification model
            # Notification.objects.create(
            #     user=document.user,
            #     title=f"Document Verified: {document.get_document_type_display()}",
            #     message=f"Your {document.get_document_type_display()} has been verified.",
            #     notification_type="document_verified",
            #     related_object_id=document.id,
            #     related_object_type="Document"
            # )

            return True
        except Exception as e:
            print(f"Error sending verification notification: {str(e)}")
            return False

    @staticmethod
    def send_fraud_detected_notification(document):
        """
        Send notification that fraud was detected in a document
        """
        try:
            # In a production app, you'd send an actual email
            print(f"[NOTIFICATION] Fraud Detected: {document.id} - {document.get_document_type_display()}")

            # You could add a record to a notification model
            # Notification.objects.create(
            #     user=document.user,
            #     title=f"Document Verification Failed: {document.get_document_type_display()}",
            #     message=f"Your {document.get_document_type_display()} could not be verified. Please check the document and resubmit.",
            #     notification_type="document_fraud",
            #     related_object_id=document.id,
            #     related_object_type="Document"
            # )

            return True
        except Exception as e:
            print(f"Error sending fraud notification: {str(e)}")
            return False

    @staticmethod
    def send_document_rejected_notification(document, rejection_reason):
        """
        Send notification that a document was manually rejected by staff
        """
        try:
            # In a production app, you'd send an actual email
            print(f"[NOTIFICATION] Document Rejected: {document.id} - {document.get_document_type_display()}")

            # You could add a record to a notification model
            # Notification.objects.create(
            #     user=document.user,
            #     title=f"Document Rejected: {document.get_document_type_display()}",
            #     message=f"Your {document.get_document_type_display()} was rejected. Reason: {rejection_reason}",
            #     notification_type="document_rejected",
            #     related_object_id=document.id,
            #     related_object_type="Document"
            # )

            return True
        except Exception as e:
            print(f"Error sending rejection notification: {str(e)}")
            return False