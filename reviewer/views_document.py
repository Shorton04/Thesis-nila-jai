from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from documents.models import Document, VerificationResult
from documents.services.document_workflow import DocumentWorkflowService
from applications.models import BusinessApplication, ApplicationRequirement
from .forms import AssessmentForm, RevisionRequestForm
from notifications.models import Notification


def is_reviewer(user):
    """Check if user is a staff member with reviewer permission"""
    return user.is_staff and user.groups.filter(name='Reviewers').exists()


@login_required
@user_passes_test(is_reviewer)
def document_detail(request, document_id):
    """View for detailed document review with AI verification results"""
    document = get_object_or_404(Document, id=document_id)

    # Get verification result if exists
    try:
        verification_result = document.result
    except VerificationResult.DoesNotExist:
        verification_result = None

    if request.method == 'POST':
        # Handle manual verification update
        verification_status = request.POST.get('verification_status')
        verification_notes = request.POST.get('verification_notes', '')

        if verification_status in ['verified', 'fraud', 'rejected']:
            # Update document verification status
            document.verification_status = verification_status

            # Update verification details with manual review information
            if not document.verification_details:
                document.verification_details = {}

            document.verification_details['manual_review'] = {
                'timestamp': timezone.now().isoformat(),
                'reviewer': request.user.get_full_name(),
                'status': verification_status,
                'notes': verification_notes
            }

            document.verification_timestamp = timezone.now()
            document.save()

            # Update any associated application requirement
            try:
                requirement = ApplicationRequirement.objects.get(
                    application=document.application,
                    requirement_name__iexact=document.document_type.replace('_', ' ')
                )

                requirement.is_verified = (verification_status == 'verified')
                requirement.verification_date = timezone.now()
                requirement.verified_by = request.user
                requirement.remarks = verification_notes
                requirement.save()
            except ApplicationRequirement.DoesNotExist:
                pass  # No matching requirement found

            # Create notification for document owner
            Notification.objects.create(
                recipient=document.user,
                title=f"Document {document.get_verification_status_display()}",
                message=f"Your document '{document.filename}' has been reviewed and marked as {document.get_verification_status_display()}." +
                        (f" Reviewer notes: {verification_notes}" if verification_notes else ""),
                notification_type='document',
                created_at=timezone.now()
            )

            messages.success(request, f"Document status updated to: {document.get_verification_status_display()}")
            return redirect('reviewer:document_detail', document_id=document.id)

    context = {
        'document': document,
        'verification_result': verification_result,
    }
    return render(request, 'reviewer/document_review.html', context)


@login_required
@user_passes_test(is_reviewer)
@require_POST
def verify_document(request, document_id):
    """API endpoint for quickly verifying a document"""
    document = get_object_or_404(Document, id=document_id)

    try:
        is_verified = request.POST.get('is_verified') == 'true'
        remarks = request.POST.get('remarks', '')

        document.verification_status = 'verified' if is_verified else 'rejected'

        # Update verification details
        if not document.verification_details:
            document.verification_details = {}

        document.verification_details['manual_review'] = {
            'timestamp': timezone.now().isoformat(),
            'reviewer': request.user.get_full_name(),
            'status': document.verification_status,
            'notes': remarks
        }

        document.verification_timestamp = timezone.now()
        document.save()

        # Update any associated application requirement
        try:
            requirement = ApplicationRequirement.objects.get(
                application=document.application,
                requirement_name__iexact=document.document_type.replace('_', ' ')
            )

            requirement.is_verified = is_verified
            requirement.verification_date = timezone.now()
            requirement.verified_by = request.user
            requirement.remarks = remarks
            requirement.save()
        except ApplicationRequirement.DoesNotExist:
            pass  # No matching requirement found

        # Create notification for document owner
        Notification.objects.create(
            recipient=document.user,
            title=f"Document {document.get_verification_status_display()}",
            message=f"Your document '{document.filename}' has been reviewed and marked as {document.get_verification_status_display()}." +
                    (f" Reviewer notes: {remarks}" if remarks else ""),
            notification_type='document',
            created_at=timezone.now()
        )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@user_passes_test(is_reviewer)
def document_analysis_api(request, document_id):
    """API endpoint to get AI analysis for document"""
    try:
        document = get_object_or_404(Document, id=document_id)

        # Get verification results
        try:
            verification_result = VerificationResult.objects.get(document=document)

            # Prepare results for frontend
            validation_results = {
                'ela_score': verification_result.fraud_probability * 100,  # Convert to percentage
                'noise_score': verification_result.verification_details.get('noise_score',
                                                                            5.0) if verification_result.verification_details else 5.0,
                'text_quality': verification_result.verification_details.get('text_quality',
                                                                             100.0) if verification_result.verification_details else 100.0,
                'resolution_score': verification_result.verification_details.get('resolution_score',
                                                                                 100.0) if verification_result.verification_details else 100.0
            }

            # Get suspicious regions for highlighting
            suspicious_regions = verification_result.fraud_areas or []

            return JsonResponse({
                'success': True,
                'results': {
                    'document_url': document.file.url,
                    'is_quarantined': document.verification_status == 'fraud',
                    'quarantine_reason': "Potential fraud detected by AI verification system" if document.verification_status == 'fraud' else None,
                    'validation_results': validation_results,
                    'validation_message': 'Document appears to be authentic and of good quality.'
                    if verification_result.is_valid
                    else 'Document shows signs of tampering or manipulation.',
                    'extracted_text': verification_result.ocr_text,
                    'suspicious_regions': suspicious_regions
                }
            })
        except VerificationResult.DoesNotExist:
            # No AI analysis yet - provide basic information
            return JsonResponse({
                'success': True,
                'results': {
                    'document_url': document.file.url,
                    'is_quarantined': False,
                    'validation_results': {
                        'ela_score': 0,
                        'noise_score': 0,
                        'text_quality': 0,
                        'resolution_score': 0
                    },
                    'validation_message': 'No AI verification has been performed on this document.',
                    'suspicious_regions': []
                }
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_reviewer)
def fraudulent_documents(request):
    """View for listing all documents flagged as potential fraud"""
    fraud_documents = Document.objects.filter(verification_status='fraud').order_by('-verification_timestamp')

    # Get verification results for each document
    documents_with_results = []
    for doc in fraud_documents:
        try:
            verification = VerificationResult.objects.get(document=doc)
            documents_with_results.append({
                'document': doc,
                'verification': verification,
                'application': doc.application
            })
        except VerificationResult.DoesNotExist:
            documents_with_results.append({
                'document': doc,
                'verification': None,
                'application': doc.application
            })

    context = {
        'documents': documents_with_results,
        'fraud_count': fraud_documents.count()
    }

    return render(request, 'reviewer/fraudulent_documents.html', context)


@login_required
@user_passes_test(is_reviewer)
def pending_documents(request):
    """View for listing all documents pending verification"""
    pending_documents = Document.objects.filter(verification_status='pending').order_by('-uploaded_at')

    context = {
        'documents': pending_documents,
        'pending_count': pending_documents.count()
    }

    return render(request, 'reviewer/pending_documents.html', context)