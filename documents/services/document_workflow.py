from datetime import datetime
from django.utils import timezone
from ..models import Document
from .document_verification import DocumentVerificationService
from .notification_service import NotificationService


class DocumentWorkflowService:
    """
    Service for handling document workflow processes:
    - Processing verification
    - Sending notifications
    - Updating application status
    """

    @staticmethod
    def process_new_document(document_id):
        """
        Process a newly uploaded document through the workflow:
        1. Run verification
        2. Send notifications based on results
        3. Update application status if needed
        """
        try:
            # Step 1: Run verification
            verification_result = DocumentVerificationService.process_document(document_id)

            if not verification_result['success']:
                return {
                    'success': False,
                    'error': verification_result['error']
                }

            document = Document.objects.get(id=document_id)

            # Step 2: Send notifications based on verification status
            if document.verification_status == 'verified':
                NotificationService.send_document_verified_notification(document)
            elif document.verification_status == 'fraud':
                NotificationService.send_fraud_detected_notification(document)

            # Step 3: Update application status if all documents are verified
            # This would typically call ApplicationService to check if all required docs are present
            # and update the application status accordingly

            return {
                'success': True,
                'document_id': document.id,
                'verification_status': document.verification_status
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

    @staticmethod
    def handle_resubmission(old_document_id, new_document_id):
        """
        Handle the resubmission of a document:
        1. Mark old document as superseded
        2. Process new document
        3. Link them together for tracking
        """
        try:
            old_document = Document.objects.get(id=old_document_id)
            new_document = Document.objects.get(id=new_document_id)

            # Update old document
            if not old_document.verification_details:
                old_document.verification_details = {}

            old_document.verification_details['superseded_by'] = {
                'document_id': new_document_id,
                'timestamp': timezone.now().isoformat()
            }
            old_document.save()

            # Process new document
            return DocumentWorkflowService.process_new_document(new_document_id)

        except Document.DoesNotExist:
            return {
                'success': False,
                'error': "Document not found"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }