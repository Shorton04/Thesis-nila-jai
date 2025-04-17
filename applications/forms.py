# applications/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    BusinessApplication, ApplicationRequirement,
    ApplicationRevision, ApplicationAssessment
)


class BusinessApplicationForm(forms.ModelForm):
    class Meta:
        model = BusinessApplication
        exclude = ['applicant', 'application_number', 'tracking_number',
                   'reviewed_by', 'approved_by', 'status', 'created_at',
                   'updated_at', 'is_active', 'closure_reason', 'closure_date',
                   'amendment_reason', 'previous_permit_number']
        widgets = {
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
            'business_area': forms.NumberInput(attrs={'step': '0.01'}),
            'capitalization': forms.NumberInput(attrs={'step': '0.01'}),
            'business_address': forms.Textarea(attrs={'rows': 3}),
            'owner_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, current_step=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_step = current_step

        # Define required fields for each step
        self.step_fields = {
            1: [
                'business_type', 'business_name', 'trade_name',
                'registration_number', 'registration_date', 'payment_mode'
            ],
            2: [
                'business_address', 'postal_code', 'telephone', 'email',
                'line_of_business', 'business_area', 'number_of_employees',
                'capitalization'
            ],
            3: [
                'owner_name', 'owner_address', 'owner_telephone', 'owner_email',
                'emergency_contact_name', 'emergency_contact_number',
                'emergency_contact_email'
            ],
            4: []  # Review step, no required fields
        }

        # Define required model fields with default values
        self.required_model_fields = {
            'business_type': 'single',
            'payment_mode': 'annually',
            'registration_date': timezone.now().date(),
            'business_area': 0,
            'number_of_employees': 0,
            'capitalization': 0,
            'line_of_business': 'Unknown',
            'business_name': 'Draft Business',
            'business_address': 'TBD',
            'postal_code': '00000',
            'telephone': 'TBD',
            'email': 'draft@example.com',
        }

        # Set all fields as not required initially
        for field in self.fields:
            self.fields[field].required = False

        # Set required fields for current step
        current_step_fields = self.step_fields.get(current_step, [])
        for field_name in current_step_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

        # Add CSS classes to all form widgets
        for field_name, field in self.fields.items():
            css_class = 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'
            field.widget.attrs['class'] = css_class

    def clean(self):
        cleaned_data = super().clean()

        # Validate fields for current step
        current_step_fields = self.step_fields.get(self.current_step, [])
        for field_name in current_step_fields:
            if field_name not in cleaned_data or not cleaned_data[field_name]:
                self.add_error(field_name, 'This field is required.')

        # Preserve existing values for fields from other steps
        if self.instance and self.instance.pk:
            for field_name, default_value in self.required_model_fields.items():
                if field_name not in current_step_fields:
                    existing_value = getattr(self.instance, field_name, None)
                    if existing_value:
                        cleaned_data[field_name] = existing_value
                    else:
                        cleaned_data[field_name] = default_value
        else:
            # For new instances, set default values for required fields
            for field_name, default_value in self.required_model_fields.items():
                if field_name not in current_step_fields and (
                        field_name not in cleaned_data or not cleaned_data[field_name]):
                    cleaned_data[field_name] = default_value

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Ensure all required fields have values
        for field_name, default_value in self.required_model_fields.items():
            current_value = getattr(instance, field_name, None)
            if not current_value and field_name not in self.step_fields.get(self.current_step, []):
                setattr(instance, field_name, default_value)

        if commit:
            instance.save()
        return instance


class RenewalApplicationForm(forms.ModelForm):
    class Meta:
        model = BusinessApplication
        fields = [
            'payment_mode', 'business_name', 'business_address',
            'postal_code', 'telephone', 'email', 'registration_date',
            'registration_number', 'gross_sales_receipts',
            'gross_essential', 'gross_non_essential', 'previous_permit_number'
        ]
        widgets = {
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'previous_permit_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current permit number'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gross_sales_receipts': forms.NumberInput(attrs={'class': 'form-control'}),
            'gross_essential': forms.NumberInput(attrs={'class': 'form-control'}),
            'gross_non_essential': forms.NumberInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set only these fields as required
        required_fields = ['payment_mode', 'business_name', 'previous_permit_number']

        for field in self.fields:
            if field in required_fields:
                self.fields[field].required = True
            else:
                self.fields[field].required = False


class AmendmentApplicationForm(forms.ModelForm):
    """Specific form for amendment applications."""

    class Meta:
        model = BusinessApplication
        fields = [
            'business_name', 'business_type', 'business_address',
            'postal_code', 'telephone', 'email', 'previous_permit_number',
            'amendment_reason'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.Select(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'previous_permit_number': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Current permit number'}),
            'amendment_reason': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Reason for amendment'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set only these fields as required
        required_fields = ['business_name', 'previous_permit_number', 'amendment_reason']

        for field in self.fields:
            if field in required_fields:
                self.fields[field].required = True
            else:
                self.fields[field].required = False


class ClosureApplicationForm(forms.ModelForm):
    """Form for business closure applications."""

    class Meta:
        model = BusinessApplication
        fields = [
            'business_name', 'registration_number', 'owner_name',
            'owner_email', 'remarks', 'closure_reason', 'closure_date',
            'previous_permit_number'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'closure_reason': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for closure'}),
            'closure_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'previous_permit_number': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Current permit number'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set only these fields as required
        required_fields = ['business_name', 'previous_permit_number', 'closure_reason', 'closure_date']

        for field in self.fields:
            if field in required_fields:
                self.fields[field].required = True
            else:
                self.fields[field].required = False

    def clean_closure_date(self):
        date = self.cleaned_data['closure_date']
        if date and date < timezone.now().date():
            raise ValidationError("Closure date cannot be in the past.")
        return date


# Keep the rest of the forms unchanged
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