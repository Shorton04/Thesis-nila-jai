# documents/services/document_verification.py
from typing import Dict
from ..utils.ocr import OCRProcessor
from ..utils.fraud_detection import FraudDetector
from ..utils.nlp_validation import NLPValidator

class DocumentVerifier:
    """Coordinates document verification process using AI services."""

    def __init__(self):
        self.ocr = OCRProcessor()
        self.fraud_detector = FraudDetector()
        self.nlp_validator = NLPValidator()

    async def verify_document(self, document_bytes, document_type: str) -> Dict:
        """
        Perform comprehensive document verification.
        Returns verification results including extracted data and fraud analysis.
        """
        try:
            # Extract text content
            if document_type.lower().endswith('pdf'):
                text_content = await self._process_async(
                    self.ocr.process_pdf, document_bytes
                )
            else:
                text_content = await self._process_async(
                    self.ocr.process_image, document_bytes
                )

            # Perform fraud detection
            fraud_results = await self._process_async(
                self.fraud_detector.analyze_document, document_bytes
            )

            # Extract and validate content
            extracted_info = await self._process_async(
                self.nlp_validator.validate_content,
                text_content.get('full_text', ''),
                document_type
            )

            # Compile verification results
            verification_results = {
                'is_verified': not fraud_results['tampering_detected'] and extracted_info['is_valid'],
                'fraud_detection': fraud_results,
                'extracted_info': extracted_info,
                'text_content': text_content
            }

            return verification_results
        except Exception as e:
            print(f"Document Verification Error: {str(e)}")
            return {
                'is_verified': False,
                'error': str(e)
            }

    @staticmethod
    async def _process_async(func, *args, **kwargs):
        """Helper method to process functions asynchronously."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def _extract_document_info(self, text_content: str, document_type: str) -> Dict:
        """Extract and validate specific information based on document type."""
        try:
            info = {'is_valid': False}

            if not text_content:
                return info

            validation_results = await self._process_async(
                self.nlp_validator.validate_content,
                text_content,
                document_type
            )

            return validation_results
        except Exception as e:
            print(f"Info Extraction Error: {str(e)}")
            return {'is_valid': False}