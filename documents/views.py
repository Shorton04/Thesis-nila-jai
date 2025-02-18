# documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Document, DocumentVerificationResult, DocumentActivity
from .forms import DocumentUploadForm
from .services.document_workflow import DocumentWorkflow
import mimetypes
from asgiref.sync import sync_to_async
import asyncio
import os


@login_required
async def upload_document(request, application_id):  # Add async here
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save the document
                document = await sync_to_async(form.save)(commit=False)
                document.application_id = application_id
                document.uploaded_by = request.user
                document.filename = request.FILES['file'].name
                document.content_type = request.FILES['file'].content_type
                document.file_size = request.FILES['file'].size
                await sync_to_async(document.save)()

                # Initialize workflow
                workflow = DocumentWorkflow()

                # Process the document
                file_content = await sync_to_async(document.file.read)()
                verification_results = await workflow.process_document(
                    file_content,
                    document.document_type
                )

                # Save verification results
                await sync_to_async(DocumentVerificationResult.objects.create)(
                    document=document,
                    is_authentic=verification_results['success'],
                    fraud_score=verification_results.get('fraud_detection_results', {}).get('confidence_score', 0.0),
                    extracted_text=verification_results.get('ocr_results', {}).get('full_text', ''),
                    extracted_data=verification_results.get('validation_results', {}),
                    verification_details=verification_results
                )

                return JsonResponse({
                    'success': True,
                    'document_id': str(document.id),
                    'verification_status': document.verification_status
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
        else:
            return JsonResponse({
                'success': False,
                'error': form.errors
            })

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


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