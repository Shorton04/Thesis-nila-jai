# documents/views.py
'''
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from .models import Document, DocumentVersion
from .utils.document_processor import DocumentProcessor
from applications.models import BusinessApplication
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@login_required
def update_document(request, document_id):
    """Handle document version updates."""
    try:
        if request.method == 'POST' and request.FILES:
            document = Document.objects.get(
                id=document_id,
                application__applicant=request.user
            )

            uploaded_file = request.FILES['document']
            notes = request.POST.get('notes', '')

            # Create new version
            latest_version = document.documentversion_set.order_by('-version_number').first()
            version_number = (latest_version.version_number + 1) if latest_version else 1

            new_version = DocumentVersion.objects.create(
                document=document,
                file=uploaded_file,
                version_number=version_number,
                notes=notes
            )

            # Process new version
            processor = DocumentProcessor()
            results = processor.process_document(
                new_version.file.path,
                document.document_type
            )

            # Update document with new results
            document.extracted_text = results.get('ocr_results', {}).get('text', '')
            document.confidence_score = results.get('ocr_results', {}).get('confidence', 0)
            document.fraud_score = results.get('fraud_detection', {}).get('fraud_score', 0)
            document.fraud_flags = results.get('fraud_detection', {}).get('flags', [])
            document.is_flagged = document.fraud_score > 0.7
            document.validation_results = results.get('validation_results', {})
            document.is_valid = all(
                validation.get('is_valid', True)
                for validation in document.validation_results.values()
            )
            document.save()

            return JsonResponse({
                'success': True,
                'version_id': new_version.id,
                'processing_results': results
            })

        return JsonResponse({
            'success': False,
            'error': 'No file uploaded'
        })

    except Document.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Document not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Document update error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def document_preview(request, document_id):
    """Generate document preview."""
    try:
        document = Document.objects.get(
            id=document_id,
            application__applicant=request.user
        )

        # Create preview if it doesn't exist
        preview_path = os.path.join(settings.MEDIA_ROOT, 'previews', f'{document_id}.jpg')

        if not os.path.exists(preview_path):
            processor = DocumentProcessor()
            processor.enhance_document_image(document.file.path)

            # Save enhanced image as preview
            os.makedirs(os.path.dirname(preview_path), exist_ok=True)
            os.system(f"convert {document.file.path} -resize 800x800 {preview_path}")

        return JsonResponse({
            'success': True,
            'preview_url': f'/media/previews/{document_id}.jpg'
        })

    except Document.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Document not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Preview generation error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def batch_upload(request, application_id):
    """Handle batch document upload."""
    try:
        if request.method != 'POST':
            return HttpResponseBadRequest('Only POST method is allowed')

        application = BusinessApplication.objects.get(
            id=application_id,
            applicant=request.user
        )

        uploaded_files = request.FILES.getlist('documents')
        document_types = request.POST.getlist('document_types')

        if len(uploaded_files) != len(document_types):
            return JsonResponse({
                'success': False,
                'error': 'Number of files and document types must match'
            }, status=400)

        processor = DocumentProcessor()
        results = []

        for file, doc_type in zip(uploaded_files, document_types):
            # Create document record
            document = Document.objects.create(
                application=application,
                document_type=doc_type,
                file=file
            )

            # Process document
            processing_results = processor.process_document(
                document.file.path,
                doc_type
            )

            # Update document with results
            document.extracted_text = processing_results.get('ocr_results', {}).get('text', '')
            document.confidence_score = processing_results.get('ocr_results', {}).get('confidence', 0)
            document.fraud_score = processing_results.get('fraud_detection', {}).get('fraud_score', 0)
            document.fraud_flags = processing_results.get('fraud_detection', {}).get('flags', [])
            document.is_flagged = document.fraud_score > 0.7
            document.validation_results = processing_results.get('validation_results', {})
            document.is_valid = all(
                validation.get('is_valid', True)
                for validation in document.validation_results.values()
            )
            document.save()

            results.append({
                'document_id': document.id,
                'document_type': doc_type,
                'processing_results': processing_results
            })

        return JsonResponse({
            'success': True,
            'results': results
        })

    except BusinessApplication.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Application not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def document_analysis(request, document_id):
    """Get detailed document analysis."""
    try:
        document = Document.objects.get(
            id=document_id,
            application__applicant=request.user
        )

        processor = DocumentProcessor()

        # Analyze document quality
        quality_analysis = processor.analyze_document_quality(document.file.path)

        # Get processing history
        versions = document.documentversion_set.all().order_by('-version_number')
        processing_history = []

        for version in versions:
            processing_history.append({
                'version': version.version_number,
                'uploaded_at': version.uploaded_at,
                'notes': version.notes
            })

        analysis_results = {
            'document_info': {
                'type': document.get_document_type_display(),
                'uploaded_at': document.uploaded_at,
                'file_name': os.path.basename(document.file.name)
            },
            'quality_analysis': quality_analysis,
            'processing_results': {
                'ocr_confidence': document.confidence_score,
                'fraud_score': document.fraud_score,
                'fraud_flags': document.fraud_flags,
                'validation_results': document.validation_results
            },
            'processing_history': processing_history
        }

        return JsonResponse({
            'success': True,
            'analysis': analysis_results
        })

    except Document.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Document not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Document analysis error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def document_download(request, document_id, version=None):
    """Download document or specific version."""
    try:
        document = Document.objects.get(
            id=document_id,
            application__applicant=request.user
        )

        if version:
            doc_version = document.documentversion_set.get(version_number=version)
            file_path = doc_version.file.path
        else:
            file_path = document.file.path

        if not os.path.exists(file_path):
            raise FileNotFoundError('Document file not found')

        # Stream file response
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response

    except (Document.DoesNotExist, DocumentVersion.DoesNotExist):
        return HttpResponseBadRequest('Document not found')
    except FileNotFoundError:
        return HttpResponseBadRequest('File not found')
    except Exception as e:
        logger.error(f"Document download error: {str(e)}")
        return HttpResponseBadRequest(f'Error downloading document: {str(e)}')
'''