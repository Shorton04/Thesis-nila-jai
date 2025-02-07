# applications/admin_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from .models import (
    BusinessApplication, ApplicationRequirement,
    ApplicationRevision, ApplicationAssessment, ApplicationActivity
)
from .forms import ApplicationAssessmentForm, RevisionRequestForm


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard showing application statistics and recent activities."""
    # Get application counts by status
    status_counts = BusinessApplication.objects.values('status').annotate(
        count=Count('id')
    )

    # Get recent applications
    recent_applications = BusinessApplication.objects.select_related('applicant').order_by(
        '-created_at'
    )[:10]

    # Get recent activities
    recent_activities = ApplicationActivity.objects.select_related(
        'application', 'performed_by'
    ).order_by('-performed_at')[:10]

    context = {
        'status_counts': status_counts,
        'recent_applications': recent_applications,
        'recent_activities': recent_activities,
    }
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def application_list(request):
    """List and filter business permit applications."""
    applications = BusinessApplication.objects.select_related('applicant').all()

    # Filter by status
    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)

    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        applications = applications.filter(
            Q(business_name__icontains=search_query) |
            Q(application_number__icontains=search_query) |
            Q(tracking_number__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(applications.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_choices': BusinessApplication.STATUS_CHOICES,
        'search_query': search_query,
        'current_status': status,
    }
    return render(request, 'admin/application_list.html', context)


@staff_member_required
def application_detail(request, application_id):
    """View and process application details."""
    application = get_object_or_404(BusinessApplication, id=application_id)
    requirements = ApplicationRequirement.objects.filter(application=application)
    activities = ApplicationActivity.objects.filter(application=application)
    revisions = ApplicationRevision.objects.filter(application=application)
    assessment = ApplicationAssessment.objects.filter(application=application).first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            application.status = 'approved'
            application.approved_by = request.user
            application.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='approve',
                performed_by=request.user,
                description='Application approved'
            )
            messages.success(request, 'Application approved successfully.')

        elif action == 'reject':
            application.status = 'rejected'
            application.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='reject',
                performed_by=request.user,
                description=f"Application rejected. Reason: {request.POST.get('remarks', '')}"
            )
            messages.success(request, 'Application rejected.')

        return redirect('admin:application_detail', application_id=application.id)

    context = {
        'application': application,
        'requirements': requirements,
        'activities': activities,
        'revisions': revisions,
        'assessment': assessment,
        'revision_form': RevisionRequestForm(),
        'assessment_form': ApplicationAssessmentForm(),
    }
    return render(request, 'admin/application_detail.html', context)


@staff_member_required
def verify_requirement(request, requirement_id):
    """Verify uploaded requirement documents."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    requirement = get_object_or_404(ApplicationRequirement, id=requirement_id)
    is_verified = request.POST.get('is_verified') == 'true'
    remarks = request.POST.get('remarks', '')

    requirement.is_verified = is_verified
    requirement.verification_date = timezone.now()
    requirement.verified_by = request.user
    requirement.remarks = remarks
    requirement.save()

    ApplicationActivity.objects.create(
        application=requirement.application,
        activity_type='review',
        performed_by=request.user,
        description=f"Document {requirement.requirement_name} {'verified' if is_verified else 'rejected'}"
    )

    return JsonResponse({'success': True})


@staff_member_required
def request_revision(request, application_id):
    """Request revisions for an application."""
    application = get_object_or_404(BusinessApplication, id=application_id)

    if request.method == 'POST':
        form = RevisionRequestForm(request.POST)
        if form.is_valid():
            revision = form.save(commit=False)
            revision.application = application
            revision.requested_by = request.user
            revision.save()

            application.status = 'requires_revision'
            application.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='revise',
                performed_by=request.user,
                description=f"Revision requested: {revision.description}"
            )

            messages.success(request, 'Revision requested successfully.')
        else:
            messages.error(request, 'Error requesting revision.')

    return redirect('admin:application_detail', application_id=application.id)


@staff_member_required
def create_assessment(request, application_id):
    """Create fee assessment for an application."""
    application = get_object_or_404(BusinessApplication, id=application_id)

    if request.method == 'POST':
        form = ApplicationAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.application = application
            assessment.assessed_by = request.user
            assessment.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='payment',
                performed_by=request.user,
                description=f"Assessment created: ₱{assessment.total_amount}"
            )

            messages.success(request, 'Assessment created successfully.')
        else:
            messages.error(request, 'Error creating assessment.')

    return redirect('admin:application_detail', application_id=application.id)


@staff_member_required
def reports(request):
    """Generate various reports and analytics."""
    # Application statistics by type
    applications_by_type = BusinessApplication.objects.values(
        'application_type'
    ).annotate(count=Count('id'))

    # Application statistics by status
    applications_by_status = BusinessApplication.objects.values(
        'status'
    ).annotate(count=Count('id'))

    # Recent assessments
    recent_assessments = ApplicationAssessment.objects.select_related(
        'application', 'assessed_by'
    ).order_by('-assessment_date')[:10]

    context = {
        'applications_by_type': applications_by_type,
        'applications_by_status': applications_by_status,
        'recent_assessments': recent_assessments,
    }
    return render(request, 'admin/reports.html', context)