# applications/models.py
from django.db import models
from accounts.models import CustomUser


class BusinessApplication(models.Model):
    APPLICATION_TYPES = (
        ('new', 'New Permit'),
        ('renewal', 'Renewal'),
        ('amendment', 'Amendment'),
        ('closure', 'Business Closure'),
    )

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('requires_revision', 'Requires Revision'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    PAYMENT_MODES = (
        ('annually', 'Annually'),
        ('semi_annually', 'Semi-Annually'),
        ('quarterly', 'Quarterly'),
    )

    BUSINESS_TYPES = (
        ('single', 'Single'),
        ('partnership', 'Partnership'),
        ('corporation', 'Corporation'),
        ('cooperative', 'Cooperative'),
        ('opc', 'One Person Corporation'),
    )

    # Basic Information
    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    application_type = models.CharField(max_length=20, choices=APPLICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES)
    registration_number = models.CharField(max_length=50)
    registration_date = models.DateField()

    # Business Details
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES)
    business_name = models.CharField(max_length=100)
    trade_name = models.CharField(max_length=100, blank=True)
    business_address = models.TextField()
    postal_code = models.CharField(max_length=10)
    telephone = models.CharField(max_length=20)
    email = models.EmailField()

    # Owner Details
    owner_name = models.CharField(max_length=100)
    owner_mobile = models.CharField(max_length=20)
    owner_email = models.EmailField()
    owner_address = models.TextField()
    owner_postal_code = models.CharField(max_length=10)

    # Business Activity
    line_of_business = models.CharField(max_length=100)
    number_of_units = models.IntegerField()
    business_area = models.DecimalField(max_digits=10, decimal_places=2)
    capitalization = models.DecimalField(max_digits=12, decimal_places=2)

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_mobile = models.CharField(max_length=20)
    emergency_contact_email = models.EmailField()

    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} - {self.application_type}"


class ApplicationRevision(models.Model):
    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField()
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Revision for {self.application.business_name}"