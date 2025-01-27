# applications/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse

from .models import (
    BusinessApplication, ApplicationRequirement, ApplicationRevision,
    ApplicationAssessment, ApplicationActivity
)
from .forms import (
    BusinessApplicationForm, RenewalApplicationForm, AmendmentApplicationForm,
    ClosureApplicationForm, ApplicationSearchForm, ApplicationReviewForm,
    PaymentVerificationForm, RequirementSubmissionForm, ApplicationCommentForm
)

@login_required
def dashboard(request):
    """Display user's application dashboard."""
    # Get user's applications
    applications = BusinessApplication.objects.filter(
        applicant=request.user,
        is_active=True
    ).order_by('-created_at')

    # Search/Filter functionality
    search_form = ApplicationSearchForm(request.GET)
    if search_form.is_valid():
        search_field = search_form.cleaned_data.get('search_field')
        search_query = search_form.cleaned_data.get('search_query')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query:
            applications = applications.filter(**{f"{search_field}__icontains": search_query})
        if status:
            applications = applications.filter(status=status)
        if date_from:
            applications = applications.filter(created_at__date__gte=date_from)
        if date_to:
            applications = applications.filter(created_at__date__lte=date_to)

    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'application_counts': {
            'total': applications.count(),
            'draft': applications.filter(status='draft').count(),
            'submitted': applications.filter(status='submitted').count(),
            'under_review': applications.filter(status='under_review').count(),
            'approved': applications.filter(status='approved').count(),
            'rejected': applications.filter(status='rejected').count(),
        }
    }

    return render(request, 'applications/dashboard.html', context)

@login_required
def new_application(request):
    """Handle new business permit application."""
    if request.method == 'POST':
        form = BusinessApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'new'
            application.save()

            # Create default requirements
            self._create_default_requirements(application)

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description='Application created'
            )

            messages.success(request, 'Application created successfully.')
            return redirect('applications:application_detail', application.id)
    else:
        form = BusinessApplicationForm()

    return render(request, 'applications/new_application.html', {
        'form': form,
        'application_type': 'new'
    })

@login_required
def renewal_application(request):
    """Handle renewal application."""
    if request.method == 'POST':
        form = RenewalApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'renewal'
            application.save()

            # Create renewal-specific requirements
            self._create_renewal_requirements(application)

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description='Renewal application created'
            )

            messages.success(request, 'Renewal application created successfully.')
            return redirect('applications:application_detail', application.id)
    else:
        form = RenewalApplicationForm()

    return render(request, 'applications/renewal_application.html', {
        'form': form,
        'application_type': 'renewal'
    })

@login_required
def amendment_application(request):
    """Handle amendment application."""
    if request.method == 'POST':
        form = AmendmentApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'amendment'
            application.save()

            # Create amendment-specific requirements
            self._create_amendment_requirements(application)

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description='Amendment application created'
            )

            messages.success(request, 'Amendment application created successfully.')
            return redirect('applications:application_detail', application.id)
    else:
        form = AmendmentApplicationForm()

    return render(request, 'applications/amendment_application.html', {
        'form': form,
        'application_type': 'amendment'
    })

@login_required
def closure_application(request):
    """Handle business closure application."""
    if request.method == 'POST':
        form = ClosureApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'closure'
            application.save()

            # Create closure-specific requirements
            self._create_closure_requirements(application)

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description='Closure application created'
            )

            messages.success(request, 'Closure application created successfully.')
            return redirect('applications:application_detail', application.id)
    else:
        form = ClosureApplicationForm()

    return render(request, 'applications/closure_application.html', {
        'form': form,
        'application_type': 'closure'
    })


@login_required
def application_detail(request, application_id):
    """Display application details."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        is_active=True
    )

    # Get requirements
    requirements = ApplicationRequirement.objects.filter(application=application)

    # Get revisions
    revisions = ApplicationRevision.objects.filter(application=application)

    # Get activities
    activities = ApplicationActivity.objects.filter(application=application)

    # Get assessment if exists
    try:
        assessment = ApplicationAssessment.objects.get(application=application)
    except ApplicationAssessment.DoesNotExist:
        assessment = None

    context = {
        'application': application,
        'requirements': requirements,
        'revisions': revisions,
        'activities': activities,
        'assessment': assessment,
        'can_edit': application.status in ['draft', 'requires_revision'],
        'can_submit': application.status == 'draft' and all(
            req.is_submitted for req in requirements if req.is_required
        ),
        'can_pay': assessment and not assessment.is_paid if assessment else False
    }

    return render(request, 'applications/application_detail.html', context)


@login_required
def edit_application(request, application_id):
    """Edit an existing application."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        is_active=True
    )

    # Check if application can be edited
    if application.status not in ['draft', 'requires_revision']:
        messages.error(request, 'This application cannot be edited.')
        return redirect('applications:application_detail', application_id)

    if request.method == 'POST':
        # Choose appropriate form based on application type
        FormClass = {
            'new': BusinessApplicationForm,
            'renewal': RenewalApplicationForm,
            'amendment': AmendmentApplicationForm,
            'closure': ClosureApplicationForm
        }[application.application_type]

        form = FormClass(request.POST, instance=application)
        if form.is_valid():
            form.save()

            # applications/views.py (continued from edit_application)
            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='update',
                performed_by=request.user,
                description='Application updated'
            )

            messages.success(request, 'Application updated successfully.')
            return redirect('applications:application_detail', application_id)
    else:
        # Choose appropriate form based on application type
        FormClass = {
            'new': BusinessApplicationForm,
            'renewal': RenewalApplicationForm,
            'amendment': AmendmentApplicationForm,
            'closure': ClosureApplicationForm
        }[application.application_type]

        form = FormClass(instance=application)

    return render(request, 'applications/edit_application.html', {
        'form': form,
        'application': application
    })


@login_required
def submit_application(request, application_id):
    """Submit application for review."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        is_active=True
    )

    if application.status != 'draft':
        messages.error(request, 'Only draft applications can be submitted.')
        return redirect('applications:application_detail', application_id)

    # Check if all required documents are uploaded
    requirements = ApplicationRequirement.objects.filter(
        application=application,
        is_required=True
    )

    missing_requirements = [req for req in requirements if not req.is_submitted]
    if missing_requirements:
        messages.error(
            request,
            'Please upload all required documents before submitting.'
        )
        return redirect('applications:application_detail', application_id)

    # Update application status
    application.status = 'submitted'
    application.submission_date = timezone.now()
    application.save()

    # Log activity
    ApplicationActivity.objects.create(
        application=application,
        activity_type='submit',
        performed_by=request.user,
        description='Application submitted for review'
    )

    messages.success(request, 'Application submitted successfully.')
    return redirect('applications:application_detail', application_id)


@login_required
def upload_requirement(request, application_id, requirement_id):
    """Handle requirement document upload."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        is_active=True
    )
    requirement = get_object_or_404(
        ApplicationRequirement,
        id=requirement_id,
        application=application
    )

    if request.method == 'POST':
        form = RequirementSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # Handle document upload and save to DocumentModel
            document = form.cleaned_data['document']
            remarks = form.cleaned_data['remarks']

            # Update requirement status
            requirement.is_submitted = True
            requirement.remarks = remarks
            requirement.save()

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='update',
                performed_by=request.user,
                description=f'Document uploaded for {requirement.requirement_name}'
            )

            messages.success(request, 'Document uploaded successfully.')
            return redirect('applications:application_detail', application_id)
    else:
        form = RequirementSubmissionForm(initial={'requirement_id': requirement_id})

    return render(request, 'applications/upload_requirement.html', {
        'form': form,
        'application': application,
        'requirement': requirement
    })


@login_required
def track_application(request, tracking_number):
    """Track application status."""
    try:
        application = BusinessApplication.objects.get(
            tracking_number=tracking_number,
            is_active=True
        )

        # Check if user has permission to view this application
        if application.applicant != request.user and not request.user.is_staff:
            messages.error(request, 'You do not have permission to view this application.')
            return redirect('applications:dashboard')

        # Get timeline of activities
        activities = ApplicationActivity.objects.filter(
            application=application
        ).order_by('performed_at')

        # Get requirements status
        requirements = ApplicationRequirement.objects.filter(
            application=application
        )

        # Get assessment details if exists
        try:
            assessment = ApplicationAssessment.objects.get(application=application)
        except ApplicationAssessment.DoesNotExist:
            assessment = None

        context = {
            'application': application,
            'activities': activities,
            'requirements': requirements,
            'assessment': assessment
        }

        return render(request, 'applications/track_application.html', context)

    except BusinessApplication.DoesNotExist:
        messages.error(request, 'Application not found.')
        return redirect('applications:dashboard')


@login_required
def cancel_application(request, application_id):
    """Cancel an application."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        is_active=True
    )

    if application.status not in ['draft', 'submitted']:
        messages.error(request, 'This application cannot be cancelled.')
        return redirect('applications:application_detail', application_id)

    if request.method == 'POST':
        # Soft delete the application
        application.is_active = False
        application.save()

        # Log activity
        ApplicationActivity.objects.create(
            application=application,
            activity_type='update',
            performed_by=request.user,
            description='Application cancelled'
        )

        messages.success(request, 'Application cancelled successfully.')
        return redirect('applications:dashboard')

    return render(request, 'applications/cancel_application.html', {
        'application': application
    })


@login_required
def application_history(request, application_id):
    """View application history and activities."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        is_active=True
    )

    activities = ApplicationActivity.objects.filter(
        application=application
    ).order_by('-performed_at')

    return render(request, 'applications/application_history.html', {
        'application': application,
        'activities': activities
    })


# Helper methods for creating requirements
def _create_default_requirements(application):
    """Create default requirements for new applications."""
    default_requirements = [
        'DTI/SEC Registration',
        'Barangay Clearance',
        'Zoning Clearance',
        'Fire Safety Inspection Certificate',
        'Sanitary Permit',
        'Environmental Clearance',
        'Location Map and Floor Plan',
    ]

    for req_name in default_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )


def _create_renewal_requirements(application):
    """Create requirements specific to renewal applications."""
    renewal_requirements = [
        'Previous Business Permit',
        'Tax Clearance',
        'Audited Financial Statement',
        'Proof of Gross Sales',
    ]

    for req_name in renewal_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )


def _create_amendment_requirements(application):
    """Create requirements specific to amendment applications."""
    amendment_requirements = [
        'Current Business Permit',
        'Supporting Documents for Amendment',
        'Proof of Payment of Amendment Fee',
    ]

    for req_name in amendment_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )


def _create_closure_requirements(application):
    """Create requirements specific to closure applications."""
    closure_requirements = [
        'Tax Clearance',
        'Affidavit of Business Closure',
        'Return of Original Business Permit',
        'Clearance from SSS/PhilHealth/Pag-IBIG',
    ]

    for req_name in closure_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )