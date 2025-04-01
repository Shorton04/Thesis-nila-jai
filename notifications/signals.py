# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from applications.models import BusinessApplication, ApplicationActivity
from documents.models import Document, VerificationResult
from .utils import send_application_notification, send_document_notification


@receiver(post_save, sender=BusinessApplication)
def application_saved(sender, instance, created, **kwargs):
    """Create notification when application status changes"""
    if not created and instance.status in ['under_review', 'requires_revision', 'approved', 'rejected']:
        send_application_notification(
            user=instance.applicant,
            application=instance,
            status=instance.status
        )


@receiver(post_save, sender=ApplicationActivity)
def application_activity_saved(sender, instance, created, **kwargs):
    """Create notification for certain application activities"""
    if created and instance.activity_type in ['revise', 'approve', 'reject']:
        # Skip if this is a self-activity (user performing action on their own application)
        if instance.performed_by == instance.application.applicant:
            return

        status_map = {
            'revise': 'requires_revision',
            'approve': 'approved',
            'reject': 'rejected'
        }

        send_application_notification(
            user=instance.application.applicant,
            application=instance.application,
            status=status_map.get(instance.activity_type, instance.application.status),
            message=instance.description
        )


@receiver(post_save, sender=VerificationResult)
def document_verified(sender, instance, created, **kwargs):
    """Create notification when document is verified or rejected"""
    if created or instance.tracker.has_changed('is_authentic'):
        status = 'verified' if instance.is_authentic else 'rejected'

        # Get the application and user
        document = instance.document
        if document.application and document.application.applicant:
            send_document_notification(
                user=document.application.applicant,
                document=document,
                status=status
            )