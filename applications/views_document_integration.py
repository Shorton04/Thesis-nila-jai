from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone

from .models import BusinessApplication, ApplicationRequirement
from documents.models import Document, VerificationResult
from documents.services.document_workflow import DocumentWorkflowService


@login_required
def document_upload_view(request, application_id):
    """Handle document upload for a specific application requirement"""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)
    requirements = ApplicationRequirement.objects.filter(application=application)

    # Get the application type to determine what documents are needed
    application_type = application.application_type

    if request.method == 'POST':
        requirement_id = request.POST.get('requirement_id')
        requirement = get_object_or_404(ApplicationRequirement, id=requirement_id, application=application)

        if 'document' in request.FILES:
            # Save the document file to the requirement
            requirement.document = request.FILES['document']
            requirement.is_submitted = True
            requirement.save()

            # Create a Document record for AI verification
            document = Document.objects.create(
                application=application,
                user=request.user,
                document_type=requirement.requirement_name.lower().replace(' ', '_'),
                file=request.FILES['document'],
                filename=request.FILES['document'].name,
                original_filename=request.FILES['document'].name,
                uploaded_at=timezone.now(),
                verification_status='pending'
            )

            # Process document through workflow (includes AI verification)
            workflow_result = DocumentWorkflowService.process_new_document(document.id)

            if workflow_result['success']:
                messages.success(
                    request,
                    f"Document uploaded and verification started. Status: {document.get_verification_status_display()}"
                )
            else:
                messages.error(
                    request,
                    f"Document uploaded but verification failed: {workflow_result.get('error', 'Unknown error')}"
                )

            # Even if verification has issues, we still mark the requirement as submitted
            return redirect('applications:application_detail', application_id=application.id)
        else:
            messages.error(request, "No document was provided")

    context = {
        'application': application,
        'requirements': requirements,
        'application_type': application_type,
    }
    return render(request, 'applications/document_upload.html', context)


@login_required
def document_status_api(request, document_id):
    """API endpoint to check document verification status"""
    try:
        document = get_object_or_404(Document, id=document_id)

        # Security check - only allow the document owner to check status
        if document.user != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)

        # Get verification result if exists
        try:
            verification = document.result
            verification_details = {
                'is_valid': verification.is_valid,
                'confidence_score': verification.confidence_score,
                'fraud_probability': verification.fraud_probability,
                'fraud_areas': verification.fraud_areas,
                'processed_at': verification.processed_at.isoformat() if verification.processed_at else None
            }
        except VerificationResult.DoesNotExist:
            verification_details = None

        return JsonResponse({
            'success': True,
            'document': {
                'id': document.id,
                'filename': document.filename,
                'verification_status': document.verification_status,
                'uploaded_at': document.uploaded_at.isoformat(),
                'verification_details': verification_details
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_application_documents(request, application_id):
    """Get all documents for an application with their verification status"""
    application = get_object_or_404(BusinessApplication, id=application_id)

    # Security check - only allow the application owner or staff to view documents
    if application.applicant != request.user and not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'error': 'Permission denied'
        }, status=403)

    documents = Document.objects.filter(application=application).order_by('-uploaded_at')
    requirements = ApplicationRequirement.objects.filter(application=application)

    # Create a mapping of requirement names to their documents
    result = []
    for req in requirements:
        req_docs = documents.filter(document_type=req.requirement_name.lower().replace(' ', '_'))

        doc_data = None
        if req_docs.exists():
            doc = req_docs.first()
            try:
                verification = doc.result
                verification_status = {
                    'is_valid': verification.is_valid,
                    'confidence_score': verification.confidence_score,
                    'fraud_probability': verification.fraud_probability
                }
            except VerificationResult.DoesNotExist:
                verification_status = None

            doc_data = {
                'id': doc.id,
                'filename': doc.filename,
                'verification_status': doc.verification_status,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'verification_details': verification_status,
                'file_url': doc.file.url if doc.file else None
            }

        result.append({
            'requirement_id': req.id,
            'requirement_name': req.requirement_name,
            'is_required': req.is_required,
            'is_submitted': req.is_submitted,
            'document': doc_data
        })

    return JsonResponse({
        'success': True,
        'application_id': str(application.id),
        'requirements': result
    })