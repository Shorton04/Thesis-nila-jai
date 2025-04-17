# reviewer/forms.py
from django import forms
from applications.models import ApplicationAssessment, ApplicationRevision

class AssessmentForm(forms.ModelForm):
    class Meta:
        model = ApplicationAssessment
        fields = ['total_amount', 'payment_deadline', 'remarks']
        widgets = {
            'total_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }

class RevisionRequestForm(forms.ModelForm):
    class Meta:
        model = ApplicationRevision
        fields = ['description', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }