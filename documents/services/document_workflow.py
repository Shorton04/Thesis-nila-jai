# documents/services/document_workflow.py
from typing import Dict
from .document_verification import DocumentVerifier
from ..utils.ocr import OCRProcessor

class DocumentWorkflow:
    """Manages the document processing and verification workflow."""

    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.document_verifier = DocumentVerifier()  # Changed from verifier to document_verifier

    async def process_document(self, file_bytes: bytes, document_type: str) -> Dict:
        """
        Process a document through the complete verification workflow.
        """
        try:
            # Verify the document using DocumentVerifier
            verification_results = await self.document_verifier.verify_document(
                file_bytes,
                document_type
            )

            # Add overall status
            verification_results['overall_status'] = self._determine_overall_status(
                verification_results
            )

            return verification_results

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'overall_status': 'failed'
            }

    def _determine_overall_status(self, results: Dict) -> str:
        """Determine the overall status based on verification results."""
        if not results.get('is_verified'):
            return 'rejected'

        fraud_results = results.get('fraud_detection', {})
        if fraud_results.get('tampering_detected'):
            return 'rejected'

        extracted_info = results.get('extracted_info', {})
        if not extracted_info.get('is_valid'):
            return 'needs_review'

        return 'accepted'