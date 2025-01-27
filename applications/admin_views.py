# applications/admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import (
    BusinessApplication, ApplicationRequirement, ApplicationRevision,
    ApplicationAssessment, ApplicationActivity
)
from .forms import (
    ApplicationReviewForm, PaymentVerificationForm, ApplicationAssessmentForm,
    ApplicationSearchForm
)


def is_staff_user(user):
    return user.is_staff


@user_passes_test(is_staff_user)
def admin_dashboard(request):
    """Admin dashboard showing application statistics and pending reviews."""
    # Get application statistics
    total_applications = BusinessApplication.objects.filter(is_active=True)
    stats = {
        'total': total_applications.count(),
        'pending_review': total_applications.filter(status='submitted').count(),
        'under_review': total_applications.filter(status='under_review').count(),
        'approved': total_applications.filter(status='approved').count(),
        'rejected': total_applications.filter(status='rejected').count(),
        'requires_revision': total_applications.filter(status='requires_revision').count()
    }

    # Get recent applications
    recent_applications = total_applications.order_by('-created_at')[:10]

    # Get applications by type
    applications_by_type = total_applications.values('application_type') \
        .annotate(count=Count('id'))

    # Get applications requiring immediate attention
    urgent_reviews = total_applications.filter(
        Q(status='submitted') |
        Q(status='under_review', updated_at__lte=timezone.now() - timezone.timedelta(days=7))
    )

    context = {
        'stats': stats,
        'recent_applications': recent_applications,
        'applications_by_type': applications_by_type,
        'urgent_reviews': urgent_reviews
    }

    return render(request, 'applications/admin/dashboard.html', context)


@user_passes_test(is_staff_user)
def application_review_list(request):
    """List of applications for review."""
    applications = BusinessApplication.objects.filter(is_active=True)

    # Handle search and filters
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
    paginator = Paginator(applications.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'applications/admin/review_list.html', {
        'page_obj': page_obj,
        'search_form': search_form
    })


@user_passes_test(is_staff_user)
def review_application(request, application_id):
    """Review a specific application."""
    application = get_object_or_404(BusinessApplication, id=application_id, is_active=True)

    if request.method == 'POST':
        form = ApplicationReviewForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            remarks = form.cleaned_data['remarks']

            if decision == 'approve':
                application.status = 'approved'
                application.approved_by = request.user
                application.remarks = remarks
                application.save()

                ActivityType = 'approve'
                description = 'Application approved'

            elif decision == 'reject':
                application.status = 'rejected'
                application.remarks = remarks
                application.save()

                ActivityType = 'reject'
                description = 'Application rejected'

            else:  # revision
                revision_deadline = form.cleaned_data['revision_deadline']
                ApplicationRevision.objects.create(
                    application=application,
                    requested_by=request.user,
                    deadline=revision_deadline,
                    description=remarks
                )
                application.status = 'requires_revision'
                application.save()

                ActivityType = 'revise'
                description = 'Revision requested'

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type=ActivityType,
                performed_by=request.user,
                description=description,
                meta_data={'remarks': remarks}
            )

            messages.success(request, f'Application {decision}d successfully.')
            return redirect('applications:admin_review_list')
    else:
        form = ApplicationReviewForm()

    # Get requirements
    requirements = ApplicationRequirement.objects.filter(application=application)

    # Get revision history
    revisions = ApplicationRevision.objects.filter(application=application)

    # Get activities
    activities = ApplicationActivity.objects.filter(application=application)

    context = {
        'application': application,
        'form': form,
        'requirements': requirements,
        'revisions': revisions,
        'activities': activities
    }

    return render(request, 'applications/admin/review_application.html', context)


@user_passes_test(is_staff_user)
def create_assessment(request, application_id):
    """Create payment assessment for approved application."""
    application = get_object_or_404(
        BusinessApplication,
        id=application_id,
        status='approved',
        is_active=True
    )

    if request.method == 'POST':
        form = ApplicationAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.application = application
            assessment.assessed_by = request.user
            assessment.save()

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='payment',
                performed_by=request.user,
                description='Payment assessment created',
                meta_data={
                    'amount': str(assessment.total_amount),
                    'deadline': assessment.payment_deadline.isoformat()
                }
            )

            messages.success(request, 'Assessment created successfully.')
            return redirect('applications:admin_review_application', application_id)
    else:
        form = ApplicationAssessmentForm()

    return render(request, 'applications/admin/create_assessment.html', {
        'form': form,
        'application': application
    })


@user_passes_test(is_staff_user)
def verify_payment(request, application_id):
    """Verify payment for an application."""
    application = get_object_or_404(BusinessApplication, id=application_id, is_active=True)
    assessment = get_object_or_404(ApplicationAssessment, application=application)

    if request.method == 'POST':
        form = PaymentVerificationForm(request.POST)
        if form.is_valid():
            payment_reference = form.cleaned_data['payment_reference']
            payment_date = form.cleaned_data['payment_date']
            amount_paid = form.cleaned_data['amount_paid']
            remarks = form.cleaned_data['remarks']

            # Update assessment
            assessment.is_paid = True
            assessment.payment_date = payment_date
            assessment.payment_reference = payment_reference
            assessment.remarks = remarks
            assessment.save()

            # Log activity
            ApplicationActivity.objects.create(
                application=application,
                activity_type='payment',
                performed_by=request.user,
                description='Payment verified',
                meta_data={
                    'payment_reference': payment_reference,
                    'amount': str(amount_paid),
                    'payment_date': payment_date.isoformat()
                }
            )

            messages.success(request, 'Payment verified successfully.')
            return redirect('applications:admin_review_application', application_id)
    else:
        form = PaymentVerificationForm()

    return render(request, 'applications/admin/verify_payment.html', {
        'form': form,
        'application': application,
        'assessment': assessment
    })


@user_passes_test(is_staff_user)
def requirement_verification(request, requirement_id):
    """Verify uploaded requirement document."""
    requirement = get_object_or_404(ApplicationRequirement, id=requirement_id)

    if request.method == 'POST':
        is_verified = request.POST.get('is_verified') == 'true'
        remarks = request.POST.get('remarks', '')

        requirement.is_verified = is_verified
        requirement.verification_date = timezone.now()
        requirement.verified_by = request.user
        requirement.remarks = remarks
        requirement.save()

        # Log activity
        ApplicationActivity.objects.create(
            application=requirement.application,
            activity_type='review',
            performed_by=request.user,
            description=f'Requirement {requirement.requirement_name} {"verified" if is_verified else "rejected"}',
            meta_data={'remarks': remarks}
        )

        return JsonResponse({
            'success': True,
            'message': 'Requirement verification updated'
        })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })