#documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from .models import Document, VerificationResult
from .forms import DocumentUploadForm, DocumentFilterForm
from .services.document_verification import DocumentVerificationService
from .services.document_workflow import DocumentWorkflowService
from .services.notification_service import NotificationService
from applications.models import BusinessApplication


@login_required
def document_upload(request, application_id):
    """
    View for uploading documents for a specific application
    """
    application = get_object_or_404(BusinessApplication, id=application_id, user=request.user)

    if request.method == 'POST':
        form = DocumentUploadForm(
            request.POST,
            request.FILES,
            application=application,
            user=request.user
        )

        if form.is_valid():
            document = form.save()

            # Process document through workflow (verification + notifications)
            workflow_result = DocumentWorkflowService.process_new_document(document.id)

            if workflow_result['success']:
                messages.success(
                    request,
                    f"Document uploaded and verification {document.verification_status}."
                )
            else:
                messages.error(
                    request,
                    f"Document uploaded but verification failed: {workflow_result['error']}"
                )

            return redirect('applications:application_detail', pk=application_id)
    else:
        form = DocumentUploadForm()

    return render(request, 'documents/upload.html', {
        'form': form,
        'application': application,
    })


@login_required
def document_list(request, application_id=None):
    """
    View for listing documents, optionally filtered by application
    """
    # Start with user's documents
    documents = Document.objects.filter(user=request.user)

    # Filter by application if provided
    if application_id:
        application = get_object_or_404(BusinessApplication, id=application_id, user=request.user)
        documents = documents.filter(application=application)

    # Process filter form
    form = DocumentFilterForm(request.GET)
    if form.is_valid():
        # Apply filters if values are provided
        if form.cleaned_data['document_type']:
            documents = documents.filter(document_type=form.cleaned_data['document_type'])

        if form.cleaned_data['status']:
            documents = documents.filter(verification_status=form.cleaned_data['status'])

        if form.cleaned_data['date_from']:
            documents = documents.filter(uploaded_at__gte=form.cleaned_data['date_from'])

        if form.cleaned_data['date_to']:
            documents = documents.filter(uploaded_at__lte=form.cleaned_data['date_to'])

    # Paginate results
    paginator = Paginator(documents.order_by('-uploaded_at'), 10)
    page_number = request.GET.get('page', 1)
    documents_page = paginator.get_page(page_number)

    return render(request, 'documents/document_list.html', {
        'documents': documents_page,
        'filter_form': form,
        'application_id': application_id,
    })


@login_required
def document_detail(request, document_id):
    """
    View for document details including verification results
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Get verification result if exists
    try:
        verification = document.result
    except VerificationResult.DoesNotExist:
        verification = None

    return render(request, 'documents/document_detail.html', {
        'document': document,
        'verification': verification,
    })


@login_required
def manual_verification(request, document_id):
    """
    Admin view for manually reviewing and updating document verification status
    """
    # Check if user is admin or staff
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('documents:document_list')

    document = get_object_or_404(Document, id=document_id)

    if request.method == 'POST':
        new_status = request.POST.get('verification_status')
        notes = request.POST.get('notes', '')

        if new_status in [status[0] for status in Document.VERIFICATION_STATUS]:
            document.verification_status = new_status

            # Update verification details
            if not document.verification_details:
                document.verification_details = {}

            document.verification_details['manual_review'] = {
                'timestamp': timezone.now().isoformat(),
                'reviewer': request.user.username,
                'status': new_status,
                'notes': notes
            }

            document.verification_timestamp = timezone.now()
            document.save()

            # Send notification if document was rejected
            if new_status == 'rejected':
                NotificationService.send_document_rejected_notification(document, notes)

            messages.success(request, f"Document verification status updated to {new_status}.")
            return redirect('documents:document_detail', document_id=document_id)

    return render(request, 'documents/review.html', {
        'document': document,
    })


@login_required
def resubmit_document(request, document_id):
    """
    View for resubmitting a document that was rejected or flagged as fraud
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Only allow resubmission if document was rejected or flagged as fraud
    if document.verification_status not in ['rejected', 'fraud']:
        messages.error(request, "This document cannot be resubmitted.")
        return redirect('documents:document_detail', document_id=document_id)

    if request.method == 'POST':
        form = DocumentUploadForm(
            request.POST,
            request.FILES,
            application=document.application,
            user=request.user
        )

        if form.is_valid():
            # Create a new document instead of updating the old one
            new_document = form.save()

            # Process resubmitted document through workflow
            workflow_result = DocumentWorkflowService.handle_resubmission(document.id, new_document.id)

            if workflow_result['success']:
                messages.success(
                    request,
                    f"Document resubmitted and verification {new_document.verification_status}."
                )
            else:
                messages.error(
                    request,
                    f"Document resubmitted but verification failed: {workflow_result['error']}"
                )

            return redirect('documents:document_detail', document_id=new_document.id)
    else:
        # Pre-fill form with document type
        form = DocumentUploadForm(initial={'document_type': document.document_type})

    return render(request, 'documents/upload.html', {
        'form': form,
        'application': document.application,
        'is_resubmission': True,
        'original_document': document,
    })