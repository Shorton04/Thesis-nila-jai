# applications/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class BusinessApplication(models.Model):
    # Application Types
    APPLICATION_TYPES = (
        ('new', 'New Permit'),
        ('renewal', 'Renewal'),
        ('amendment', 'Amendment'),
        ('closure', 'Business Closure'),
    )

    # Status Choices
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('requires_revision', 'Requires Revision'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    )

    # Payment Modes
    PAYMENT_MODES = (
        ('annually', 'Annually'),
        ('semi_annually', 'Semi-Annually'),
        ('quarterly', 'Quarterly'),
    )

    # Business Types
    BUSINESS_TYPES = (
        ('single', 'Single Proprietorship'),
        ('partnership', 'Partnership'),
        ('corporation', 'Corporation'),
        ('cooperative', 'Cooperative'),
        ('opc', 'One Person Corporation'),
    )

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application_type = models.CharField(max_length=20, choices=APPLICATION_TYPES)
    application_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES)
    tracking_number = models.CharField(max_length=50, unique=True)
    submission_date = models.DateTimeField(null=True, blank=True)
    is_released = models.BooleanField(default=False)
    release_date = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_applications'
    )

    # Business Details - Make fields optional for renewal, amendment, closure
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, blank=True, null=True)
    business_name = models.CharField(max_length=255)
    trade_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    business_address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Business Activity - Make fields optional
    line_of_business = models.CharField(max_length=100, blank=True)
    business_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    number_of_employees = models.PositiveIntegerField(null=True, blank=True)
    capitalization = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Owner Details - Make fields optional
    owner_name = models.CharField(max_length=255, blank=True)
    owner_address = models.TextField(blank=True)
    owner_telephone = models.CharField(max_length=20, blank=True)
    owner_email = models.EmailField(blank=True)

    # Emergency Contact - Make fields optional
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True)
    emergency_contact_email = models.EmailField(blank=True)

    # Financial Information (for renewal)
    gross_sales_receipts = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    gross_essential = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    gross_non_essential = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_applications'
    )
    remarks = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Additional fields for amendment and closure
    closure_reason = models.TextField(blank=True)  # For closure applications
    closure_date = models.DateField(null=True, blank=True)  # For closure applications
    amendment_reason = models.TextField(blank=True)  # For amendment applications
    previous_permit_number = models.CharField(max_length=50, blank=True)  # For renewal/amendment

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status']),
            models.Index(fields=['business_name']),
        ]

    def __str__(self):
        return f"{self.business_name} - {self.application_number}"

    def save(self, *args, **kwargs):
        # Generate application number if not exists
        if not self.application_number:
            year = timezone.now().year
            count = BusinessApplication.objects.filter(
                created_at__year=year
            ).count() + 1
            self.application_number = f"BP-{year}-{count:05d}"

        # Generate tracking number if not exists
        if not self.tracking_number:
            self.tracking_number = f"TRK-{uuid.uuid4().hex[:8].upper()}"

        super().save(*args, **kwargs)

# Keep the rest of the models unchanged
class ApplicationRequirement(models.Model):
    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    requirement_name = models.CharField(max_length=255)
    document = models.FileField(upload_to='requirements/%Y/%m/%d/', null=True, blank=True)
    is_required = models.BooleanField(default=True)
    is_submitted = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ApplicationRevision(models.Model):
    """Model for tracking application revisions and changes."""

    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    revision_number = models.PositiveIntegerField()
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_revisions'
    )
    requested_date = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField()
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_date = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_revisions'
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_date']

    def __str__(self):
        return f"Revision {self.revision_number} - {self.application.application_number}"

    def save(self, *args, **kwargs):
        # Set revision number if not exists
        if not self.revision_number:
            last_revision = ApplicationRevision.objects.filter(
                application=self.application
            ).order_by('-revision_number').first()
            self.revision_number = (last_revision.revision_number + 1) if last_revision else 1
        super().save(*args, **kwargs)


class ApplicationAssessment(models.Model):
    """Model for tracking application assessments and fees."""

    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assessment_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_deadline = models.DateTimeField()
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Assessment - {self.application.application_number}"


class ApplicationActivity(models.Model):
    """Model for tracking all activities related to an application."""

    ACTIVITY_TYPES = (
        ('create', 'Created'),
        ('update', 'Updated'),
        ('submit', 'Submitted'),
        ('review', 'Reviewed'),
        ('revise', 'Revision Requested'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('payment', 'Payment'),
        ('comment', 'Comment Added'),
    )

    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    performed_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-performed_at']
        verbose_name_plural = 'Application activities'

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.application.application_number}"