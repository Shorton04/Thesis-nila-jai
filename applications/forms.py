# applications/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    BusinessApplication, ApplicationRequirement,
    ApplicationRevision, ApplicationAssessment
)


class BusinessApplicationForm(forms.ModelForm):
    """Form for creating and updating business permit applications."""

    class Meta:
        model = BusinessApplication
        exclude = ['applicant', 'application_number', 'tracking_number',
                   'reviewed_by', 'approved_by', 'status', 'created_at',
                   'updated_at', 'is_active']

        widgets = {
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
            'submission_date': forms.DateInput(attrs={'type': 'date'}),
            'business_area': forms.NumberInput(attrs={'step': '0.01'}),
            'capitalization': forms.NumberInput(attrs={'step': '0.01'}),
            'gross_sales_receipts': forms.NumberInput(attrs={'step': '0.01'}),
            'gross_essential': forms.NumberInput(attrs={'step': '0.01'}),
            'gross_non_essential': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def clean_registration_date(self):
        date = self.cleaned_data['registration_date']
        if date > timezone.now().date():
            raise ValidationError("Registration date cannot be in the future.")
        return date

    def clean_business_area(self):
        area = self.cleaned_data['business_area']
        if area <= 0:
            raise ValidationError("Business area must be greater than 0.")
        return area

    def clean_capitalization(self):
        capitalization = self.cleaned_data['capitalization']
        if capitalization <= 0:
            raise ValidationError("Capitalization must be greater than 0.")
        return capitalization

    def clean(self):
        cleaned_data = super().clean()
        application_type = cleaned_data.get('application_type')

        # Validate financial information for renewal applications
        if application_type == 'renewal':
            if not cleaned_data.get('gross_sales_receipts'):
                raise ValidationError({
                    'gross_sales_receipts': "This field is required for renewal applications."
                })


class RenewalApplicationForm(BusinessApplicationForm):
    """Specific form for renewal applications with additional validation."""

    previous_permit_number = forms.CharField(max_length=20)
    previous_permit_expiry = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta(BusinessApplicationForm.Meta):
        fields = BusinessApplicationForm.Meta.exclude + ['previous_permit_number', 'previous_permit_expiry']

    def clean_previous_permit_expiry(self):
        expiry_date = self.cleaned_data['previous_permit_expiry']
        if expiry_date > timezone.now().date():
            raise ValidationError("Previous permit has not expired yet.")
        return expiry_date


class AmendmentApplicationForm(BusinessApplicationForm):
    """Specific form for amendment applications."""

    amendment_reason = forms.CharField(widget=forms.Textarea)
    current_permit_number = forms.CharField(max_length=20)

    class Meta(BusinessApplicationForm.Meta):
        fields = BusinessApplicationForm.Meta.exclude + ['amendment_reason', 'current_permit_number']


class ClosureApplicationForm(forms.ModelForm):
    """Form for business closure applications."""

    class Meta:
        model = BusinessApplication
        fields = ['business_name', 'registration_number', 'owner_name',
                  'owner_email', 'remarks']

    closure_reason = forms.CharField(widget=forms.Textarea)
    closure_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def clean_closure_date(self):
        date = self.cleaned_data['closure_date']
        if date < timezone.now().date():
            raise ValidationError("Closure date cannot be in the past.")
        return date


class ApplicationRequirementForm(forms.ModelForm):
    """Form for managing application requirements."""

    class Meta:
        model = ApplicationRequirement
        fields = ['requirement_name', 'is_required', 'remarks']


class ApplicationRevisionForm(forms.ModelForm):
    """Form for requesting application revisions."""

    class Meta:
        model = ApplicationRevision
        fields = ['description', 'deadline']
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }


class ApplicationAssessmentForm(forms.ModelForm):
    """Form for creating application assessments."""

    class Meta:
        model = ApplicationAssessment
        fields = ['total_amount', 'payment_deadline', 'remarks']
        widgets = {
            'payment_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'total_amount': forms.NumberInput(attrs={'step': '0.01'})
        }

    def clean_total_amount(self):
        amount = self.cleaned_data['total_amount']
        if amount <= 0:
            raise ValidationError("Total amount must be greater than 0.")
        return amount

    def clean_payment_deadline(self):
        deadline = self.cleaned_data['payment_deadline']
        if deadline < timezone.now():
            raise ValidationError("Payment deadline must be in the future.")
        return deadline


class ApplicationSearchForm(forms.Form):
    """Form for searching applications."""

    SEARCH_FIELDS = (
        ('application_number', 'Application Number'),
        ('tracking_number', 'Tracking Number'),
        ('business_name', 'Business Name'),
        ('owner_name', 'Owner Name'),
    )

    search_field = forms.ChoiceField(choices=SEARCH_FIELDS)
    search_query = forms.CharField(max_length=100, required=False)
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(BusinessApplication.STATUS_CHOICES),
        required=False
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        if date_from and date_to and date_from > date_to:
            raise ValidationError("Start date must be before end date.")

        return cleaned_data


class ApplicationReviewForm(forms.Form):
    """Form for reviewing applications."""

    DECISION_CHOICES = (
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('revise', 'Request Revision'),
    )

    decision = forms.ChoiceField(choices=DECISION_CHOICES)
    remarks = forms.CharField(widget=forms.Textarea, required=False)
    revision_deadline = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        revision_deadline = cleaned_data.get('revision_deadline')

        if decision == 'revise' and not revision_deadline:
            raise ValidationError({
                'revision_deadline': "Revision deadline is required when requesting revision."
            })

        if decision == 'revise' and revision_deadline < timezone.now():
            raise ValidationError({
                'revision_deadline': "Revision deadline must be in the future."
            })

        return cleaned_data


class PaymentVerificationForm(forms.Form):
    """Form for verifying application payments."""

    payment_reference = forms.CharField(max_length=50)
    payment_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    amount_paid = forms.DecimalField(max_digits=15, decimal_places=2)
    remarks = forms.CharField(widget=forms.Textarea, required=False)

    def clean_payment_date(self):
        payment_date = self.cleaned_data['payment_date']
        if payment_date > timezone.now():
            raise ValidationError("Payment date cannot be in the future.")
        return payment_date

    def clean_amount_paid(self):
        amount = self.cleaned_data['amount_paid']
        if amount <= 0:
            raise ValidationError("Amount paid must be greater than 0.")
        return amount


class RequirementSubmissionForm(forms.Form):
    """Form for submitting application requirements."""

    requirement_id = forms.IntegerField(widget=forms.HiddenInput)
    document = forms.FileField()
    remarks = forms.CharField(widget=forms.Textarea, required=False)

    def clean_document(self):
        document = self.cleaned_data['document']
        if document:
            # Check file size (10MB limit)
            if document.size > 10 * 1024 * 1024:
                raise ValidationError("File size must not exceed 10MB.")

            # Check file extension
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_extension = document.name.lower()[document.name.lower().rfind('.'):]
            if file_extension not in allowed_extensions:
                raise ValidationError(
                    f"Only {', '.join(allowed_extensions)} files are allowed."
                )

        return document


class ApplicationCommentForm(forms.Form):
    """Form for adding comments to applications."""

    comment = forms.CharField(widget=forms.Textarea)
    visibility = forms.ChoiceField(choices=[
        ('public', 'Public - Visible to applicant'),
        ('internal', 'Internal - Staff only'),
    ])