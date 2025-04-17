# applications/utils.py

import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from documents.models import Document
from .models import (
    BusinessApplication, ApplicationRequirement, ApplicationActivity
)


def generate_tracking_number():
    """Generate a unique tracking number for applications."""
    timestamp = timezone.now().strftime('%Y%m%d')
    random_str = str(uuid.uuid4().hex)[:6].upper()
    return f"TRK-{timestamp}-{random_str}"


def validate_permit_number(permit_number):
    """Validate permit number format."""
    if not permit_number.startswith('BP-'):
        raise ValidationError("Invalid permit number format")
    return permit_number


def handle_document_upload(file, application, requirement):
    """Handle document upload and verification."""
    # Create document record
    document = Document.objects.create(
        file=file,
        application=application,
        requirement=requirement,
        uploaded_by=application.applicant
    )

    # Update requirement status
    requirement.is_submitted = True
    requirement.save()

    return document


def validate_closure_date(closure_date):
    """Validate closure date is at least 14 days in the future."""
    min_date = timezone.now().date() + timezone.timedelta(days=14)
    if closure_date < min_date:
        raise ValidationError("Closure date must be at least 14 days from today")


def validate_renewal_eligibility(previous_permit_expiry):
    """Validate renewal eligibility based on permit expiry."""
    if previous_permit_expiry > timezone.now().date():
        raise ValidationError("Previous permit has not expired yet")


def create_requirements_for_application(application):
    """Create requirements based on application type."""
    requirement_types = {
        'new': [
            ('DTI/SEC Registration', True),
            ('Barangay Clearance', True),
            ('Fire Safety Inspection', True),
            ('Sanitary Permit', True),
            ('Zoning Clearance', True),
            ('Occupancy Permit', False),
            ('Environmental Clearance', False),
        ],
        'renewal': [
            ('Previous Business Permit', True),
            ('Tax Clearance', True),
            ('Financial Statement', True),
            ('Fire Safety Inspection', True),
            ('Sanitary Permit', True),
        ],
        'amendment': [
            ('Current Business Permit', True),
            ('Supporting Documents', True),
            ('Proof of Amendment', True),
        ],
        'closure': [
            ('Affidavit of Closure', True),
            ('Tax Clearance', True),
            ('Final Financial Statement', True),
            ('Return of Business Permit', True),
        ]
    }

    for name, required in requirement_types.get(application.application_type, []):
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=name,
            is_required=required
        )


@transaction.atomic
def submit_application(application, user):
    """Handle application submission process."""
    # Validate required documents
    missing_requirements = ApplicationRequirement.objects.filter(
        application=application,
        is_required=True,
        is_submitted=False
    )

    if missing_requirements.exists():
        raise ValidationError("All required documents must be submitted")

    # Update application status
    application.status = 'submitted'
    application.submission_date = timezone.now()
    application.save()

    # Create activity log
    ApplicationActivity.objects.create(
        application=application,
        activity_type='submit',
        performed_by=user,
        description='Application submitted for review'
    )


@transaction.atomic
def process_amendment(application, amendment_data):
    """Handle amendment application processing."""
    amendment_type = amendment_data.get('amendment_type')

    if amendment_type == 'business_name':
        application.business_name = amendment_data.get('updated_business_name')
    elif amendment_type == 'address':
        application.business_address = amendment_data.get('updated_address')
        application.postal_code = amendment_data.get('postal_code')
    elif amendment_type == 'ownership':
        # Create ownership transfer record
        application.previous_owner = amendment_data.get('previous_owner')
        application.new_owner = amendment_data.get('new_owner')

    application.amendment_reason = amendment_data.get('amendment_reason')
    application.save()


@transaction.atomic
def process_closure(application, closure_data):
    """Handle closure application processing."""
    validate_closure_date(closure_data.get('closure_date'))

    application.closure_date = closure_data.get('closure_date')
    application.closure_reason = closure_data.get('closure_reason')
    application.save()


def calculate_completion_percentage(application):
    """Calculate application completion percentage."""
    requirements = ApplicationRequirement.objects.filter(
        application=application,
        is_required=True
    )

    if not requirements.exists():
        return 0

    submitted = requirements.filter(is_submitted=True).count()
    total = requirements.count()

    return (submitted / total) * 100


def get_application_requirements(application):
    """Get structured requirements data for an application."""
    return ApplicationRequirement.objects.filter(
        application=application
    ).select_related('document').order_by('created_at')


# applications/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from .forms import (
    BusinessApplicationForm, RenewalApplicationForm,
    AmendmentApplicationForm, ClosureApplicationForm,
    RequirementSubmissionForm
)
from .models import BusinessApplication
from .utils import (
    generate_tracking_number, validate_permit_number,
    handle_document_upload, validate_renewal_eligibility,
    create_requirements_for_application, submit_application,
    process_amendment, process_closure, calculate_completion_percentage,
    get_application_requirements
)


@login_required
def handle_file_upload(request, application_id, requirement_id):
    """Handle file upload for application requirements."""
    try:
        application = get_object_or_404(
            BusinessApplication,
            id=application_id,
            applicant=request.user
        )
        requirement = get_object_or_404(
            ApplicationRequirement,
            id=requirement_id,
            application=application
        )

        if request.method == 'POST' and request.FILES.get('document'):
            try:
                document = handle_document_upload(
                    request.FILES['document'],
                    application,
                    requirement
                )
                return JsonResponse({
                    'success': True,
                    'message': 'Document uploaded successfully',
                    'document_id': str(document.id)
                })
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
        return JsonResponse({
            'success': False,
            'error': 'Invalid request'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def submit_for_review(request, application_id):
    """Submit application for review."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        status='draft'
    )

    try:
        submit_application(application, request.user)
        messages.success(request, 'Application submitted successfully')
        return redirect('applications:application_detail', application_id=application_id)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('applications:application_detail', application_id=application_id)


@login_required
def save_draft(request, application_id):
    """Save application as draft."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user
    )

    try:
        form_data = request.POST.copy()
        form_data['status'] = 'draft'

        if application.application_type == 'new':
            form = BusinessApplicationForm(form_data, instance=application)
        elif application.application_type == 'renewal':
            form = RenewalApplicationForm(form_data, instance=application)
        elif application.application_type == 'amendment':
            form = AmendmentApplicationForm(form_data, instance=application)
        else:  # closure
            form = ClosureApplicationForm(form_data, instance=application)

        if form.is_valid():
            form.save()
            messages.success(request, 'Draft saved successfully')
        else:
            raise ValidationError("Invalid form data")

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def get_application_status(request, application_id):
    """Get application status and completion percentage."""
    try:
        application = get_object_or_404(
            BusinessApplication,
            id=application_id,
            applicant=request.user
        )

        completion = calculate_completion_percentage(application)
        requirements = get_application_requirements(application)

        requirement_status = [{
            'id': req.id,
            'name': req.requirement_name,
            'required': req.is_required,
            'submitted': req.is_submitted,
            'verified': req.is_verified,
            'remarks': req.remarks
        } for req in requirements]

        return JsonResponse({
            'success': True,
            'status': application.status,
            'completion_percentage': completion,
            'requirements': requirement_status
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })