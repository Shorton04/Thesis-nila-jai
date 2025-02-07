# reviewer/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from applications.models import (
    BusinessApplication, ApplicationRequirement,
    ApplicationRevision, ApplicationAssessment, ApplicationActivity
)
from .forms import AssessmentForm, RevisionRequestForm


def is_reviewer(user):
    return user.is_staff and user.groups.filter(name='Reviewers').exists()


@user_passes_test(is_reviewer)
def dashboard(request):
    pending_applications = BusinessApplication.objects.filter(status='submitted').count()
    under_review = BusinessApplication.objects.filter(status='under_review').count()
    requires_revision = BusinessApplication.objects.filter(status='requires_revision').count()

    recent_applications = BusinessApplication.objects.filter(
        status__in=['submitted', 'under_review']
    ).order_by('-submission_date')[:5]

    recent_activities = ApplicationActivity.objects.filter(
        application__status__in=['submitted', 'under_review', 'requires_revision']
    ).order_by('-performed_at')[:10]

    context = {
        'pending_applications': pending_applications,
        'under_review': under_review,
        'requires_revision': requires_revision,
        'recent_applications': recent_applications,
        'recent_activities': recent_activities
    }
    return render(request, 'reviewer/dashboard.html', context)


@user_passes_test(is_reviewer)
def application_list(request):
    applications = BusinessApplication.objects.all()

    # Filter by status
    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)

    # Filter by type
    app_type = request.GET.get('type')
    if app_type:
        applications = applications.filter(application_type=app_type)

    # Search
    search = request.GET.get('search')
    if search:
        applications = applications.filter(
            Q(business_name__icontains=search) |
            Q(application_number__icontains=search)
        )

    paginator = Paginator(applications.order_by('-submission_date'), 20)
    page = request.GET.get('page')
    applications = paginator.get_page(page)

    context = {
        'applications': applications,
        'current_status': status,
        'current_type': app_type,
        'search': search
    }
    return render(request, 'reviewer/application_list.html', context)


@user_passes_test(is_reviewer)
def application_detail(request, application_id):
    application = get_object_or_404(BusinessApplication, id=application_id)
    requirements = ApplicationRequirement.objects.filter(application=application)
    activities = ApplicationActivity.objects.filter(application=application)
    assessment = ApplicationAssessment.objects.filter(application=application).first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'start_review':
            application.status = 'under_review'
            application.reviewed_by = request.user
            application.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='review',
                performed_by=request.user,
                description='Review started'
            )

            messages.success(request, 'Review started.')

        elif action == 'request_revision':
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

        elif action == 'approve':
            if not assessment:
                messages.error(request, 'Cannot approve without assessment.')
                return redirect('reviewer:application_detail', application_id=application.id)

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
            reason = request.POST.get('reject_reason')
            if not reason:
                messages.error(request, 'Rejection reason is required.')
                return redirect('reviewer:application_detail', application_id=application.id)

            application.status = 'rejected'
            application.remarks = reason
            application.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='reject',
                performed_by=request.user,
                description=f'Application rejected. Reason: {reason}'
            )

            messages.success(request, 'Application rejected.')

        return redirect('reviewer:application_detail', application_id=application.id)

    context = {
        'application': application,
        'requirements': requirements,
        'activities': activities,
        'assessment': assessment,
        'revision_form': RevisionRequestForm(),
        'assessment_form': AssessmentForm() if not assessment else None
    }
    return render(request, 'reviewer/application_detail.html', context)


@user_passes_test(is_reviewer)
def verify_requirement(request, requirement_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    requirement = get_object_or_404(ApplicationRequirement, id=requirement_id)

    try:
        is_verified = request.POST.get('is_verified') == 'true'
        remarks = request.POST.get('remarks', '')

        requirement.is_verified = is_verified
        requirement.verification_date = timezone.now()
        requirement.verified_by = request.user
        requirement.remarks = remarks
        requirement.save()

        ApplicationActivity.objects.create(
            application=requirement.application,
            activity_type='verify_document',
            performed_by=request.user,
            description=f'Document {requirement.requirement_name} {"verified" if is_verified else "rejected"}'
        )

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@user_passes_test(is_reviewer)
def create_assessment(request, application_id):
    application = get_object_or_404(BusinessApplication, id=application_id)

    if request.method == 'POST':
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.application = application
            assessment.assessed_by = request.user
            assessment.save()

            ApplicationActivity.objects.create(
                application=application,
                activity_type='assessment',
                performed_by=request.user,
                description=f'Assessment created: ₱{assessment.total_amount}'
            )

            messages.success(request, 'Assessment created successfully.')
        else:
            messages.error(request, 'Invalid assessment data.')

    return redirect('reviewer:application_detail', application_id=application.id)