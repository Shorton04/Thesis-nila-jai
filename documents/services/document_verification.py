import os
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from ..utils.ocr import extract_text_from_document
from ..utils.fraud_detection import detect_fraud
from ..models import Document, VerificationResult


class DocumentVerificationService:
    """
    Service for processing document verification.
    This simulates AI document processing but actually just checks filenames.
    """

    @staticmethod
    def process_document(document_id):
        """
        Process a document for verification.
        """
        try:
            document = Document.objects.get(id=document_id)

            # Get the file path
            file_path = os.path.join(settings.MEDIA_ROOT, document.file.name)

            # Extract text using OCR (simulated)
            ocr_result = extract_text_from_document(file_path)

            # Detect fraud (simulated)
            fraud_result = detect_fraud(file_path, document.document_type)

            # Create or update verification result
            verification_result, created = VerificationResult.objects.update_or_create(
                document=document,
                defaults={
                    'is_valid': fraud_result['is_valid'],
                    'confidence_score': fraud_result['confidence_score'],
                    'fraud_probability': fraud_result['fraud_probability'],
                    'fraud_areas': fraud_result['fraud_areas'],
                    'ocr_text': ocr_result['text'],
                    'processed_at': timezone.now(),
                }
            )

            # Update document status
            if fraud_result['is_valid']:
                document.verification_status = 'verified'
            else:
                document.verification_status = 'fraud'

            document.verification_details = {
                'ocr': ocr_result,
                'fraud_detection': fraud_result,
                'processed_at': datetime.now().isoformat()
            }
            document.verification_timestamp = timezone.now()
            document.save()

            return {
                'success': True,
                'document_id': document.id,
                'verification_status': document.verification_status,
                'details': document.verification_details
            }

        except Document.DoesNotExist:
            return {
                'success': False,
                'error': f"Document with ID {document_id} not found"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }