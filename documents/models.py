# documents/models.py
from django.db import models
from django.conf import settings
from applications.models import BusinessApplication
import uuid
import os

def document_upload_path(instance, filename):
    # Generate path like: documents/application_id/document_type/filename
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('documents', str(instance.application.id), instance.document_type, filename)

class Document(models.Model):
    DOCUMENT_TYPES = [
        ('dti_registration', 'DTI Registration'),
        ('business_permit', 'Business Permit'),
        ('valid_id', 'Valid ID'),
        ('lease_contract', 'Lease Contract'),
        ('sanitary_permit', 'Sanitary Permit'),
        ('fire_safety', 'Fire Safety Permit'),
        ('barangay_clearance', 'Barangay Clearance'),
        ('zoning_clearance', 'Zoning Clearance'),
        ('tax_declaration', 'Tax Declaration'),
        ('other', 'Other Document')
    ]

    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('quarantined', 'Quarantined')
    ]

    QUARANTINE_REASONS = [
        ('tampering', 'Signs of Tampering'),
        ('low_quality', 'Low Quality'),
        ('suspicious_noise', 'Suspicious Noise Patterns'),
        ('resolution', 'Poor Resolution'),
        ('other', 'Other')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to=document_upload_path)
    filename = models.CharField(max_length=255, default='document.pdf')  # Added default
    content_type = models.CharField(max_length=100, default='application/pdf')  # Added default
    file_size = models.IntegerField(default=0)  # Added default
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Changed to SET_NULL
        null=True,
        blank=True,
        related_name='uploaded_documents'  # Added related_name
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_remarks = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_quarantined = models.BooleanField(default=False)
    quarantine_reason = models.CharField(
        max_length=50,
        choices=QUARANTINE_REASONS,
        null=True,
        blank=True
    )
    quarantine_date = models.DateTimeField(null=True, blank=True)
    quarantine_notes = models.TextField(blank=True)
    release_date = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_documents'
    )

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['application', 'document_type']),
            models.Index(fields=['verification_status']),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.filename}"

    def get_file_extension(self):
        return os.path.splitext(self.filename)[1].lower()

    def is_image(self):
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        return self.get_file_extension() in image_extensions

    def is_pdf(self):
        return self.get_file_extension() == '.pdf'


class DocumentVerificationResult(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE)
    verification_id = models.UUIDField(default=uuid.uuid4, editable=False)
    is_authentic = models.BooleanField(default=False)
    fraud_score = models.FloatField(default=0.0)
    extracted_text = models.TextField(blank=True)
    extracted_data = models.JSONField(default=dict)
    verification_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Verification Result - {self.document.filename}"


class DocumentActivity(models.Model):
    ACTIVITY_TYPES = [
        ('upload', 'Upload'),
        ('verify', 'Verify'),
        ('reject', 'Reject'),
        ('delete', 'Delete'),
        ('view', 'View')
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Changed to SET_NULL
        null=True  # Added null=True
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-performed_at']
        verbose_name_plural = 'Document activities'

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.document.filename}"