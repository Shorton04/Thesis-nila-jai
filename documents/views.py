# documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Document, DocumentVerificationResult, DocumentActivity
from .forms import DocumentUploadForm
from .services.document_workflow import DocumentWorkflow
import mimetypes
from .utils.document_validator import DocumentValidator
from .utils.quarantine_manager import QuarantineManager
from asgiref.sync import sync_to_async
import asyncio
import os


@login_required
async def upload_document(request, application_id):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create document instance
                document = form.save(commit=False)
                document.application_id = application_id
                document.uploaded_by = request.user

                # Validate document
                validator = DocumentValidator()
                is_valid, results, message = validator.validate_document(
                    request.FILES['file'].read()
                )

                # Save validation results
                document.metadata = {
                    'validation_results': results,
                    'validation_message': message,
                    'validation_date': timezone.now().isoformat()
                }

                # Check if document should be quarantined
                quarantine_reason = validator.determine_quarantine_reason(results)

                if quarantine_reason:
                    document.save()  # Save first to get ID
                    quarantine = QuarantineManager(document)
                    quarantine.quarantine(
                        reason=quarantine_reason,
                        notes=message,
                        user=request.user
                    )

                    return JsonResponse({
                        'success': False,
                        'quarantined': True,
                        'reason': quarantine_reason,
                        'message': message
                    })

                # Save valid document
                document.save()

                return JsonResponse({
                    'success': True,
                    'document_id': str(document.id),
                    'message': 'Document uploaded successfully'
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def view_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    # Check permissions
    if not (request.user == document.uploaded_by or
            request.user.groups.filter(name='Reviewers').exists()):
        raise PermissionDenied

    try:
        # Log document view
        DocumentActivity.objects.create(
            document=document,
            activity_type='view',
            performed_by=request.user
        )

        file_path = document.file.path
        content_type, encoding = mimetypes.guess_type(file_path)

        if content_type is None:
            content_type = 'application/octet-stream'

        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=content_type)

        # Set content-disposition
        if document.is_image():
            response['Content-Disposition'] = f'inline; filename="{document.filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{document.filename}"'

        return response

    except Exception as e:
        messages.error(request, f'Error accessing document: {str(e)}')
        return redirect('applications:application_detail', application_id=document.application.id)


@login_required
def delete_document(request, document_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    document = get_object_or_404(Document, id=document_id)

    # Check permissions
    if request.user != document.uploaded_by:
        return JsonResponse({
            'success': False,
            'error': 'Permission denied'
        }, status=403)

    try:
        # Create activity log before deletion
        DocumentActivity.objects.create(
            document=document,
            activity_type='delete',
            performed_by=request.user,
            details='Document deleted by user'
        )

        # Delete the file and document
        document.file.delete()
        document.delete()

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def document_verification_status(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    # Check permissions
    if not (request.user == document.uploaded_by or
            request.user.groups.filter(name='Reviewers').exists()):
        raise PermissionDenied

    try:
        verification_result = DocumentVerificationResult.objects.get(document=document)

        return JsonResponse({
            'success': True,
            'status': document.verification_status,
            'is_authentic': verification_result.is_authentic,
            'fraud_score': verification_result.fraud_score,
            'verification_details': verification_result.verification_details
        })

    except DocumentVerificationResult.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Verification result not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def upload_document(request, application_id):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create document instance
                document = form.save(commit=False)
                document.application_id = application_id
                document.uploaded_by = request.user

                # Validate document
                validator = DocumentValidator()
                is_valid, results, message = validator.validate_document(
                    request.FILES['file'].read()
                )

                if not is_valid:
                    return JsonResponse({
                        'success': False,
                        'error': message
                    })

                # Save validation results
                document.metadata = {
                    'validation_results': results,
                    'validation_message': message
                }

                # Save document
                document.save()

                return JsonResponse({
                    'success': True,
                    'document_id': str(document.id),
                    'validation_message': message
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
@user_passes_test(lambda u: u.is_staff)
def quarantine_list(request):
    """View quarantined documents"""
    quarantined = Document.objects.filter(is_quarantined=True)
    return render(request, 'documents/quarantine_list.html', {
        'documents': quarantined
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def release_from_quarantine(request, document_id):
    """Release document from quarantine"""
    if request.method == 'POST':
        document = get_object_or_404(Document, id=document_id)
        notes = request.POST.get('notes', '')

        quarantine = QuarantineManager(document)
        quarantine.release(request.user, notes)

        messages.success(request, 'Document released from quarantine')
        return redirect('documents:quarantine_list')