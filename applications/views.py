from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
import mimetypes
import os
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import (
    BusinessApplication, ApplicationRequirement,
    ApplicationRevision, ApplicationAssessment, ApplicationActivity
)
from .forms import (
    BusinessApplicationForm, RenewalApplicationForm,
    AmendmentApplicationForm, ClosureApplicationForm,
    ApplicationSearchForm, RequirementSubmissionForm
)
import uuid


@login_required
def dashboard(request):
    """Dashboard view showing application statistics and list."""
    search_form = ApplicationSearchForm(request.GET)
    applications = BusinessApplication.objects.filter(applicant=request.user)

    if search_form.is_valid():
        search_field = search_form.cleaned_data.get('search_field')
        search_query = search_form.cleaned_data.get('search_query')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query:
            filter_kwargs = {f"{search_field}__icontains": search_query}
            applications = applications.filter(**filter_kwargs)

        if status:
            applications = applications.filter(status=status)

        if date_from:
            applications = applications.filter(created_at__gte=date_from)
        if date_to:
            applications = applications.filter(created_at__lte=date_to)

    # Get application counts
    application_counts = {
        'total': applications.count(),
        'draft': applications.filter(status='draft').count(),
        'submitted': applications.filter(status='submitted').count(),
        'approved': applications.filter(status='approved').count(),
        'rejected': applications.filter(status='rejected').count(),
    }

    # Pagination
    paginator = Paginator(applications.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'application_counts': application_counts,
    }
    return render(request, 'applications/dashboard.html', context)


STEP_TEMPLATES = {
    1: 'applications/steps/basic_information.html',
    2: 'applications/steps/business_details.html',
    3: 'applications/steps/owner_details.html',
    4: 'applications/steps/review.html'
}


@login_required
def new_application(request):
    """Handle new business permit application with multi-step form."""
    current_step = int(request.session.get('application_step', 1))
    total_steps = 4
    draft_id = request.session.get('draft_application_id')
    draft_application = None

    if draft_id:
        try:
            draft_application = BusinessApplication.objects.get(
                id=draft_id,
                applicant=request.user,
                status='draft'
            )
        except BusinessApplication.DoesNotExist:
            request.session.pop('draft_application_id', None)

    if request.method == 'POST':
        form = BusinessApplicationForm(
            request.POST,
            instance=draft_application,
            current_step=current_step
        )
        action = request.POST.get('action', '')

        if action == 'previous':
            if current_step > 1:
                request.session['application_step'] = current_step - 1
            return redirect('applications:new_application')

        if form.is_valid():
            try:
                # Save form with required fields
                application = form.save(commit=False)
                application.applicant = request.user
                application.application_type = 'new'
                application.status = 'draft'

                # Set defaults for non-current step fields if needed
                if not application.business_area:
                    application.business_area = 0
                if not application.number_of_employees:
                    application.number_of_employees = 0
                if not application.capitalization:
                    application.capitalization = 0

                application.save()
                request.session['draft_application_id'] = str(application.id)

                if action == 'save_draft':
                    messages.success(request, 'Application saved as draft.')
                    return redirect('applications:application_detail', application.id)

                elif action == 'continue':
                    next_step = current_step + 1
                    if next_step <= total_steps:
                        request.session['application_step'] = next_step
                        return redirect('applications:new_application')
                    else:
                        # Final submission
                        application.status = 'submitted'
                        application.submission_date = timezone.now()
                        application.save()

                        ApplicationActivity.objects.create(
                            application=application,
                            activity_type='create',
                            performed_by=request.user,
                            description='Application created and submitted'
                        )

                        create_default_requirements(application)

                        # Clear session
                        request.session.pop('application_step', None)
                        request.session.pop('draft_application_id', None)

                        messages.success(request, 'Application submitted successfully.')
                        return redirect('applications:application_detail', application.id)

            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
                print(f"Error saving form: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = BusinessApplicationForm(
            instance=draft_application,
            current_step=current_step
        )

    context = {
        'form': form,
        'current_step': current_step,
        'total_steps': total_steps,
        'step_template': STEP_TEMPLATES.get(current_step),
    }
    return render(request, 'applications/new_application.html', context)


@login_required
def renewal_application(request):
    """Handle business permit renewal application."""
    if request.method == 'POST':
        form = RenewalApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'renewal'

            if request.POST.get('action') == 'save_draft':
                application.status = 'draft'
                messages.success(request, 'Renewal application saved as draft.')
            else:
                application.status = 'submitted'
                application.submission_date = timezone.now()
                messages.success(request, 'Renewal application submitted successfully.')

            application.save()

            # Create activity log
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description='Renewal application created'
            )

            # Create renewal-specific requirements
            create_renewal_requirements(application)

            return redirect('applications:application_detail', application.id)
    else:
        form = RenewalApplicationForm()

    return render(request, 'applications/renewal_application.html', {'form': form})


@login_required
def amendment_application(request):
    """Handle business permit amendment application."""
    if request.method == 'POST':
        form = AmendmentApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'amendment'

            if request.POST.get('action') == 'save_draft':
                application.status = 'draft'
                messages.success(request, 'Amendment application saved as draft.')
            else:
                application.status = 'submitted'
                application.submission_date = timezone.now()
                messages.success(request, 'Amendment application submitted successfully.')

            application.save()

            # Create activity log
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description='Amendment application created'
            )

            # Create amendment-specific requirements
            create_amendment_requirements(application)

            return redirect('applications:application_detail', application.id)
    else:
        form = AmendmentApplicationForm()

    return render(request, 'applications/amendment_application.html', {'form': form})


@login_required
def closure_application(request):
    """Handle business closure application."""
    if request.method == 'POST':
        form = ClosureApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'closure'

            if request.POST.get('action') == 'save_draft':
                application.status = 'draft'
                messages.success(request, 'Closure application saved as draft.')
            else:
                application.status = 'submitted'
                application.submission_date = timezone.now()
                messages.success(request, 'Closure application submitted successfully.')

            application.save()

            # Create activity log
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description='Closure application created'
            )

            # Create closure-specific requirements
            create_closure_requirements(application)

            return redirect('applications:application_detail', application.id)
    else:
        form = ClosureApplicationForm()

    return render(request, 'applications/closure_application.html', {'form': form})


@login_required
def application_detail(request, application_id):
    """Display application details and handle status updates."""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
    requirements = ApplicationRequirement.objects.filter(application=application)
    activities = ApplicationActivity.objects.filter(application=application)
    assessment = ApplicationAssessment.objects.filter(application=application).first()

    # Calculate completion percentage
    total_requirements = requirements.count()
    completed_requirements = requirements.filter(is_submitted=True).count()
    completion_percentage = (completed_requirements / total_requirements * 100) if total_requirements > 0 else 0

    # Determine user permissions
    can_edit = application.status in ['draft', 'requires_revision']
    can_submit = application.status == 'draft'
    can_pay = assessment and not assessment.is_paid

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'submit' and can_submit:
            application.status = 'submitted'
            application.submission_date = timezone.now()
            application.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='submit',
                performed_by=request.user,
                description='Application submitted for review'
            )

            messages.success(request, 'Application submitted successfully.')
            return redirect('applications:application_detail', application.id)

        elif action == 'cancel':
            application.status = 'cancelled'
            application.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='cancel',
                performed_by=request.user,
                description='Application cancelled'
            )

            messages.success(request, 'Application cancelled successfully.')
            return redirect('applications:dashboard')

    context = {
        'application': application,
        'requirements': requirements,
        'activities': activities,
        'assessment': assessment,
        'completion_percentage': completion_percentage,
        'can_edit': can_edit,
        'can_submit': can_submit,
        'can_pay': can_pay,
    }
    return render(request, 'applications/application_detail.html', context)


@login_required
def upload_requirement(request, application_id, requirement_id):
    """Handle document upload for application requirements."""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
    requirement = get_object_or_404(ApplicationRequirement, id=requirement_id, application=application)

    if request.method == 'POST':
        form = RequirementSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            document = request.FILES['document']

            # Save the document and update requirement status
            requirement.document = document
            requirement.is_submitted = True
            requirement.remarks = form.cleaned_data.get('remarks', '')
            requirement.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='update',
                performed_by=request.user,
                description=f'Document uploaded for {requirement.requirement_name}'
            )

            messages.success(request, 'Document uploaded successfully.')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid form submission',
                'errors': form.errors
            })

    form = RequirementSubmissionForm(initial={'requirement_id': requirement.id})
    context = {
        'form': form,
        'application': application,
        'requirement': requirement,
    }
    return render(request, 'applications/upload_requirement.html', context)


# Helper functions
def create_default_requirements(application):
    """Create default requirements for new applications."""
    default_requirements = [
        'Proof of Registration (DTI/SEC/CDA)',
        'Proof of Legal Ownership',
        'Picture with Signage',
        'Fire Safety Inspection Certificate',
        'Zoning Clearance',
        'Occupancy Permit',
        'Sanitary Permit',
        'Barangay Clearance'
    ]

    for req_name in default_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )


def create_renewal_requirements(application):
    """Create requirements specific to renewal applications."""
    renewal_requirements = [
        'Previous Business Permit',
        'Proof of Annual Gross Receipts',
        'Sworn Declaration of Gross Sales',
        'Tax Returns (2550M, 2550Q, 2551Q)'
    ]

    for req_name in renewal_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )


def create_amendment_requirements(application):
    """Create requirements specific to amendment applications."""
    amendment_requirements = [
        'Board Resolution (if applicable)',
        'Updated DTI/SEC/CDA Registration',
        'Proof of Legal Ownership for New Address',
        'Updated Contract of Lease',
        'Photo of Business Establishment'
    ]

    for req_name in amendment_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )


def create_closure_requirements(application):
    """Create requirements specific to closure applications."""
    closure_requirements = [
        'Latest Original Business Permit',
        'Business Registration Plate',
        'Barangay Business Closure Certificate',
        'Affidavit of Closure',
        'Proof of Tax Payment'
    ]

    for req_name in closure_requirements:
        ApplicationRequirement.objects.create(
            application=application,
            requirement_name=req_name,
            is_required=True
        )


@login_required
def view_requirement(request, application_id, requirement_id):
    """View a requirement document."""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
    requirement = get_object_or_404(ApplicationRequirement, id=requirement_id, application=application)

    if not requirement.document:
        messages.error(request, 'No document available.')
        return redirect('applications:requirements', application_id=application_id)

    try:
        file_path = requirement.document.path
        content_type, encoding = mimetypes.guess_type(file_path)

        if content_type is None:
            content_type = 'application/octet-stream'

        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=content_type)

        # Set content-disposition based on file type
        if content_type.startswith('image/'):
            # Display images in browser
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
        else:
            # Download other files
            response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)

        return response

    except Exception as e:
        messages.error(request, f'Error accessing document: {str(e)}')
        return redirect('applications:requirements', application_id=application_id)


@login_required
def requirements(request, application_id):
    """Display and manage application requirements."""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
    requirements = ApplicationRequirement.objects.filter(application=application)

    context = {
        'application': application,
        'requirements': requirements,
    }
    return render(request, 'applications/requirements.html', context)


@login_required
def upload_requirement(request, application_id, requirement_id):
    """Handle requirement document upload."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
    requirement = get_object_or_404(ApplicationRequirement, id=requirement_id, application=application)

    try:
        if 'document' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No document provided'})

        document = request.FILES['document']

        # Validate file size (10MB limit)
        if document.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'File size must not exceed 10MB'})

        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif']
        if document.content_type not in allowed_types:
            return JsonResponse({'success': False, 'error': 'Invalid file type'})

        # Save the document
        requirement.document = document
        requirement.remarks = request.POST.get('remarks', '')
        requirement.is_submitted = True
        requirement.updated_at = timezone.now()
        requirement.save()

        # Log the activity
        ApplicationActivity.objects.create(
            application=application,
            activity_type='update',
            performed_by=request.user,
            description=f'Document uploaded for {requirement.requirement_name}'
        )

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def application_history(request, application_id):
    """Display application history and timeline."""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)

    # Get all activities sorted by performed_at in descending order
    activities = ApplicationActivity.objects.filter(
        application=application
    ).select_related('performed_by').order_by('-performed_at')

    context = {
        'application': application,
        'activities': activities,
    }
    return render(request, 'applications/history.html', context)