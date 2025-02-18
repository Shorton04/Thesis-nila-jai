# applications/views.py
from django.shortcuts import render, redirect, get_object_or_404
from documents.services.document_workflow import DocumentWorkflow
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
import mimetypes
import os
import logging
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
    applications = BusinessApplication.objects.filter(applicant=request.user)

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
        'application_counts': application_counts,
    }
    return render(request, 'applications/dashboard.html', context)


logger = logging.getLogger(__name__)

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
        print(f"POST data: {request.POST}")
        form = BusinessApplicationForm(
            request.POST,
            instance=draft_application,
            current_step=current_step
        )

        # Get the action from submit_type
        action = request.POST.get('submit_type')
        print(f"Action: {action}")

        if action == 'previous' and current_step > 1:
            request.session['application_step'] = current_step - 1
            return redirect('applications:new_application')

        if form.is_valid():
            try:
                application = form.save(commit=False)
                application.applicant = request.user
                application.application_type = 'new'
                application.status = 'draft'
                application.save()

                # Store application ID in session
                request.session['draft_application_id'] = str(application.id)

                if action == 'save_draft':
                    messages.success(request, 'Application saved as draft.')
                    return redirect('applications:application_detail', application.id)

                elif action == 'continue':
                    next_step = current_step + 1
                    if next_step <= total_steps:
                        request.session['application_step'] = next_step
                        messages.success(request, f'Step {current_step} completed.')
                        return redirect('applications:new_application')
                    else:
                        # Final submission
                        application.status = 'submitted'
                        application.submission_date = timezone.now()
                        application.save()

                        # Create activity log and requirements
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
            print(f"Form errors: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
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
    if request.method == 'POST':
        form = RenewalApplicationForm(request.POST, request.FILES)

        try:
            application = form.save(commit=False)
            application.applicant = request.user
            application.application_type = 'renewal'

            # Set status based on action
            action = request.POST.get('action', '')
            application.status = 'draft' if action == 'save_draft' else 'submitted'

            if application.status == 'submitted':
                application.submission_date = timezone.now()

            application.save()

            # Handle required documents
            required_docs = {
                'business_permit': 'Previous Business Permit',
                'sales_declaration': 'Gross Sales Declaration',
                'tax_returns': 'Tax Returns'
            }

            for key, name in required_docs.items():
                if key in request.FILES:
                    requirement = ApplicationRequirement.objects.create(
                        application=application,
                        requirement_name=name,
                        document=request.FILES[key],
                        is_submitted=True
                    )

            # Create activity log
            ApplicationActivity.objects.create(
                application=application,
                activity_type='create',
                performed_by=request.user,
                description=f'Renewal application {application.status}'
            )

            success_msg = 'Application saved as draft.' if action == 'save_draft' else 'Renewal application submitted successfully.'
            messages.success(request, success_msg)

            return redirect('applications:application_detail', application.id)

        except Exception as e:
            print(f"Error in renewal application: {str(e)}")  # For debugging
            messages.error(request, f'Error processing application: {str(e)}')
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
def requirement_upload(request, application_id, requirement_id):
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
        content_type = document.content_type.lower()
        if content_type not in allowed_types:
            return JsonResponse({'success': False, 'error': 'Invalid file type. Only PDF and images are allowed.'})

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
def view_requirement(request, application_id, requirement_id):
    """View a requirement document."""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
    requirement = get_object_or_404(ApplicationRequirement, id=requirement_id, application=application)

    if not requirement.document:
        messages.error(request, 'No document available.')
        return redirect('applications:application_detail', application_id=application.id)

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
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        else:
            # Download other files
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'

        return response

    except Exception as e:
        messages.error(request, f'Error accessing document: {str(e)}')
        return redirect('applications:application_detail', application_id=application.id)


@login_required
def edit_application(request, application_id):
    """Handle editing of business permit application."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        applicant=request.user,
        status__in=['draft', 'requires_revision']
    )

    if request.method == 'POST':
        form = BusinessApplicationForm(request.POST, instance=application)
        if form.is_valid():
            application = form.save(commit=False)

            if 'save_draft' in request.POST:
                application.status = 'draft'
                messages.success(request, 'Changes saved as draft.')
            elif 'submit' in request.POST:
                application.status = 'submitted'
                application.submission_date = timezone.now()
                messages.success(request, 'Application submitted successfully.')

            application.save()

            # Log the activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='update',
                performed_by=request.user,
                description='Application details updated'
            )

            return redirect('applications:application_detail', application_id=application.id)
    else:
        form = BusinessApplicationForm(instance=application)

    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'applications/edit_application.html', context)


@login_required
def upload_requirement(request, application_id, requirement_id):
    """Handle requirement document upload."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
        requirement = get_object_or_404(ApplicationRequirement, id=requirement_id, application=application)

        if 'document' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No document provided'})

        document = request.FILES['document']

        # Validate file size (10MB limit)
        if document.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'File size must not exceed 10MB'})

        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        content_type = document.content_type.lower()
        if content_type not in allowed_types:
            return JsonResponse({'success': False, 'error': 'Invalid file type. Only PDF and images are allowed.'})

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


@login_required
def status_detail(request, application_id):
    """Handle status detail view for an application."""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)

    # Get requirements with submission status
    requirements = ApplicationRequirement.objects.filter(application=application)
    total_requirements = requirements.filter(is_required=True).count()
    completed_requirements = requirements.filter(is_required=True, is_submitted=True).count()
    completion_percentage = (completed_requirements / total_requirements * 100) if total_requirements > 0 else 0

    # Get application timeline
    activities = ApplicationActivity.objects.filter(
        application=application
    ).select_related('performed_by').order_by('-performed_at')

    # Check permissions for various actions
    can_edit = application.status in ['draft', 'requires_revision']
    can_submit = application.status == 'draft' and completion_percentage == 100
    can_pay = hasattr(application, 'assessment') and not application.assessment.is_paid

    # Handle POST requests (submit/cancel actions)
    if request.method == 'POST':
        action = request.POST.get('action')

        try:
            if action == 'submit' and can_submit:
                with transaction.atomic():
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

            elif action == 'cancel' and application.status == 'draft':
                with transaction.atomic():
                    application.status = 'cancelled'
                    application.save()

                    ApplicationActivity.objects.create(
                        application=application,
                        activity_type='cancel',
                        performed_by=request.user,
                        description='Application cancelled' +
                                    (f": {request.POST.get('cancel_reason')}" if request.POST.get(
                                        'cancel_reason') else '')
                    )

                messages.success(request, 'Application cancelled successfully.')
                return redirect('applications:dashboard')

        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')
            return redirect('applications:status_detail', application.id)

    context = {
        'application': application,
        'requirements': requirements,
        'activities': activities,
        'total_requirements': total_requirements,
        'completed_requirements': completed_requirements,
        'completion_percentage': completion_percentage,
        'can_edit': can_edit,
        'can_submit': can_submit,
        'can_pay': can_pay,
    }

    return render(request, 'applications/status_detail.html', context)


@login_required
def delete_requirement(request, application_id, requirement_id):
    """Handle deletion of an application requirement document."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        application = get_object_or_404(BusinessApplication,
                                        id=application_id,
                                        applicant=request.user)

        # Only allow deletion if application is in draft or requires revision
        if application.status not in ['draft', 'requires_revision']:
            raise PermissionDenied('Cannot modify requirements at this stage')

        requirement = get_object_or_404(ApplicationRequirement,
                                        id=requirement_id,
                                        application=application)

        if requirement.document:
            # Delete the actual file
            requirement.document.delete(save=False)

            # Update requirement status
            requirement.is_submitted = False
            requirement.is_verified = False
            requirement.verification_date = None
            requirement.verified_by = None
            requirement.remarks = ''
            requirement.save()

            # Log the activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='update',
                performed_by=request.user,
                description=f'Document deleted for {requirement.requirement_name}'
            )

            return JsonResponse({
                'success': True,
                'message': 'Document deleted successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No document found'
            })

    except PermissionDenied as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=403)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error deleting document: {str(e)}'
        }, status=500)


@login_required
def status_update(request, application_id):
    """API endpoint for checking application status updates."""
    try:
        application = get_object_or_404(BusinessApplication,
                                        id=application_id,
                                        applicant=request.user)

        return JsonResponse({
            'status': application.status,
            'updated_at': application.updated_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)