# documents/models.py
from django.db import models
from django.core.validators import FileExtensionValidator
from applications.models import BusinessApplication


class Document(models.Model):
    DOCUMENT_TYPES = (
        ('dti_sec_registration', 'DTI/SEC Registration'),
        ('business_permit', 'Business Permit'),
        ('lease_contract', 'Lease Contract'),
        ('fire_safety', 'Fire Safety Certificate'),
        ('sanitary_permit', 'Sanitary Permit'),
        ('barangay_clearance', 'Barangay Clearance'),
        ('other', 'Other'),
    )

    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    # OCR Results
    extracted_text = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0.0)

    # Fraud Detection Results
    fraud_score = models.FloatField(default=0.0)
    fraud_flags = models.JSONField(default=dict)
    is_flagged = models.BooleanField(default=False)

    # NLP Validation Results
    validation_results = models.JSONField(default=dict)
    is_valid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.application.business_name}"


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    file = models.FileField(
        upload_to='documents/versions/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    version_number = models.IntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f"Version {self.version_number} of {self.document}"