from django.db import models
from django.conf import settings
from applications.models import BusinessApplication
import uuid


def document_upload_path(instance, filename):
    """
    Define the upload path for document files.
    Files will be uploaded to MEDIA_ROOT/documents/user_<id>/<document_type>/<filename>
    """
    # Get the extension of the uploaded file
    ext = filename.split('.')[-1]
    # Construct the new filename using document type and original filename
    new_filename = f"{instance.document_type}_{filename}"
    # Return the upload path
    return f'documents/user_{instance.user.id}/{instance.document_type}/{new_filename}'


class Document(models.Model):
    DOCUMENT_TYPES = (
        ('dti_sec', 'DTI/SEC Registration'),
        ('lease', 'Contract of Lease'),
        ('title', 'Transfer Certificate of Title'),
        ('consent', 'Notarized Consent'),
        ('signage', 'Picture with Signage'),
        ('fire_cert', 'Fire Safety Inspection Certificate'),
        ('zoning', 'Zoning Clearance'),
        ('hoa', 'HOA Permit'),
        ('occupancy', 'Occupancy Permit'),
        ('sanitary', 'Sanitary Permit'),
        ('barangay', 'Barangay Clearance'),
        ('gross_receipt', 'Proof of Annual Gross Receipts'),
        ('sale_deed', 'Deed of Absolute Sale'),
        ('transfer', 'Deed of Assignment/Transfer of Rights'),
        ('closure', 'Affidavit of Closure'),
        ('board_resolution', 'Board Resolution'),
    )

    VERIFICATION_STATUS = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('fraud', 'Potential Fraud Detected'),
        ('rejected', 'Rejected'),
    )

    application = models.ForeignKey(
        BusinessApplication,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to=document_upload_path)
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    verification_details = models.JSONField(null=True, blank=True)
    verification_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.application}"


class VerificationResult(models.Model):
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='result'
    )
    is_valid = models.BooleanField(default=False)
    confidence_score = models.FloatField(default=0.0)
    fraud_probability = models.FloatField(default=0.0)
    fraud_areas = models.JSONField(null=True, blank=True)
    ocr_text = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Verification for {self.document}"