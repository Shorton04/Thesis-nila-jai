from django import forms
from django.core.exceptions import ValidationError
from .models import Document
from .services.document_verification_utils import validate_file_extension, get_document_naming_pattern


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'file']

    def __init__(self, *args, **kwargs):
        self.application = kwargs.pop('application', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Add classes for styling
        self.fields['document_type'].widget.attrs.update({
            'class': 'form-control',
            'id': 'document_type'
        })
        self.fields['file'].widget.attrs.update({
            'class': 'form-control-file',
            'id': 'document_file'
        })

        # Add help text for file naming
        self.fields['file'].help_text = "For proper AI verification, follow the naming pattern for your document type."

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Validate file extension
            validate_file_extension(file)
        return file

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.application:
            instance.application = self.application

        if self.user:
            instance.user = self.user

        # Save original filename
        if instance.file:
            instance.original_filename = instance.file.name
            # Store the cleaned up filename
            instance.filename = instance.file.name.split('/')[-1]

        if commit:
            instance.save()

        return instance


class DocumentFilterForm(forms.Form):
    """
    Form for filtering documents in the document list view
    """
    STATUS_CHOICES = (
        ('', 'All Statuses'),
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('fraud', 'Potential Fraud Detected'),
        ('rejected', 'Rejected'),
    )

    document_type = forms.ChoiceField(
        choices=[(None, 'All Types')] + list(Document.DOCUMENT_TYPES),
        required=False
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add classes for styling
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
            })