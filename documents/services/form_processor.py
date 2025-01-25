# documents/services/form_processor.py

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from django.core.files.base import File
from django.conf import settings
from ..models import Document, BusinessApplication
from ..utils.ocr import OCRProcessor
from ..utils.fraud_detection import FraudDetector
from ..utils.nlp_validation import NLPValidator
import json
import os

logger = logging.getLogger(__name__)


class FormProcessingService:
    """
    Service class responsible for processing business permit application forms
    and their associated documents.
    """

    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.fraud_detector = FraudDetector()
        self.nlp_validator = NLPValidator()

    def process_application_form(self, application_data: Dict[str, Any], files: Dict[str, File]) -> Dict[str, Any]:
        """
        Process a complete business permit application form submission.
        """
        try:
            processing_results = {
                'success': True,
                'validation_results': {},
                'extracted_data': {},
                'fraud_detection': {},
                'errors': []
            }

            # Validate form data
            validation_results = self._validate_form_data(application_data)
            processing_results['validation_results'] = validation_results

            if not validation_results.get('is_valid', False):
                processing_results['success'] = False
                processing_results['errors'].extend(validation_results.get('issues', []))
                return processing_results

            # Process uploaded documents
            document_results = self._process_documents(files)
            processing_results.update(document_results)

            # Cross-validate form data with extracted document data
            cross_validation = self._cross_validate_data(
                application_data,
                document_results.get('extracted_data', {})
            )

            if not cross_validation['is_valid']:
                processing_results['success'] = False
                processing_results['errors'].extend(cross_validation['issues'])

            # Store processing results
            self._store_processing_results(processing_results)

            return processing_results

        except Exception as e:
            logger.error(f"Error processing application form: {str(e)}")
            return {
                'success': False,
                'errors': [f"Error processing application: {str(e)}"]
            }

    def _validate_form_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all form fields using NLP validation.
        """
        try:
            validation_results = self.nlp_validator.validate_all_fields(form_data)

            # Additional business-specific validations
            business_validations = self._perform_business_validations(form_data)
            validation_results['business_validations'] = business_validations

            # Update overall validity
            validation_results['is_valid'] = (
                    validation_results.get('is_valid', True) and
                    business_validations.get('is_valid', True)
            )

            return validation_results

        except Exception as e:
            logger.error(f"Form validation error: {str(e)}")
            return {
                'is_valid': False,
                'issues': [f"Validation error: {str(e)}"]
            }

    def _process_documents(self, files: Dict[str, File]) -> Dict[str, Any]:
        """
        Process and validate all uploaded documents.
        """
        results = {
            'success': True,
            'extracted_data': {},
            'fraud_detection': {},
            'errors': []
        }

        for doc_type, file in files.items():
            try:
                # Save temporary file for processing
                temp_path = self._save_temp_file(file)

                # Perform OCR
                ocr_results = self.ocr_processor.process_document(temp_path)
                results['extracted_data'][doc_type] = ocr_results.get('fields', {})

                # Perform fraud detection
                fraud_results = self.fraud_detector.analyze_document(temp_path)
                results['fraud_detection'][doc_type] = fraud_results

                # Clean up temporary file
                os.remove(temp_path)

                # Check for high fraud scores
                if fraud_results.get('fraud_score', 0) > settings.FRAUD_DETECTION_THRESHOLD:
                    results['errors'].append(
                        f"Potential fraud detected in {doc_type} document"
                    )
                    results['success'] = False

            except Exception as e:
                logger.error(f"Error processing document {doc_type}: {str(e)}")
                results['errors'].append(f"Error processing {doc_type}: {str(e)}")
                results['success'] = False

        return results

    def _cross_validate_data(self, form_data: Dict[str, Any],
                             extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cross-validate form input data with extracted document data.
        """
        validation_results = {
            'is_valid': True,
            'matches': [],
            'discrepancies': [],
            'issues': []
        }

        # Key fields to cross-validate
        fields_to_validate = {
            'business_name': 'exact',
            'registration_number': 'exact',
            'owner_name': 'fuzzy',
            'business_address': 'fuzzy'
        }

        for field, match_type in fields_to_validate.items():
            form_value = form_data.get(field)
            extracted_value = None

            # Look for the field in extracted data from all documents
            for doc_data in extracted_data.values():
                if field in doc_data:
                    extracted_value = doc_data[field]
                    break

            if form_value and extracted_value:
                if match_type == 'exact':
                    if form_value.lower() != extracted_value.lower():
                        validation_results['discrepancies'].append({
                            'field': field,
                            'form_value': form_value,
                            'extracted_value': extracted_value
                        })
                        validation_results['issues'].append(
                            f"Mismatch in {field}: form shows '{form_value}' but document shows '{extracted_value}'"
                        )
                else:  # fuzzy matching
                    similarity = self._calculate_similarity(form_value, extracted_value)
                    if similarity < settings.FUZZY_MATCH_THRESHOLD:
                        validation_results['discrepancies'].append({
                            'field': field,
                            'form_value': form_value,
                            'extracted_value': extracted_value,
                            'similarity': similarity
                        })
                        validation_results['issues'].append(
                            f"Possible mismatch in {field}: form shows '{form_value}' but document shows '{extracted_value}'"
                        )
            else:
                validation_results['issues'].append(
                    f"Unable to cross-validate {field}: missing data in form or documents"
                )

        validation_results['is_valid'] = len(validation_results['discrepancies']) == 0
        return validation_results

    def _perform_business_validations(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform business-specific validations on the form data.
        """
        validations = {
            'is_valid': True,
            'issues': []
        }

        # Validate business capitalization
        capitalization = form_data.get('capitalization')
        if capitalization:
            cap_validation = self.nlp_validator.validate_capitalization(capitalization)
            if not cap_validation['is_valid']:
                validations['is_valid'] = False
                validations['issues'].extend(cap_validation['issues'])

        # Validate business area
        business_area = form_data.get('business_area')
        business_type = form_data.get('business_type')
        if business_area and business_type:
            area_validation = self.nlp_validator.validate_business_area(
                business_area,
                business_type
            )
            if not area_validation['is_valid']:
                validations['is_valid'] = False
                validations['issues'].extend(area_validation['issues'])

        # Validate business activity
        business_activity = form_data.get('business_activity')
        line_of_business = form_data.get('line_of_business')
        if business_activity and line_of_business:
            activity_validation = self.nlp_validator.validate_business_activity(
                business_activity,
                line_of_business
            )
            if not activity_validation['is_valid']:
                validations['is_valid'] = False
                validations['issues'].extend(activity_validation['issues'])

        return validations

    def _save_temp_file(self, file: File) -> str:
        """
        Save uploaded file to temporary location for processing.
        """
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        temp_path = os.path.join(temp_dir, f"temp_{file.name}")
        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return temp_path

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings.
        """
        # Use NLP validator's string similarity function
        return self.nlp_validator.calculate_string_similarity(str1, str2)

    def _store_processing_results(self, results: Dict[str, Any]) -> None:
        """
        Store processing results for future reference and analytics.
        """
        try:
            results_dir = os.path.join(settings.MEDIA_ROOT, 'processing_results')
            os.makedirs(results_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"processing_results_{timestamp}.json"

            with open(os.path.join(results_dir, filename), 'w') as f:
                json.dump(results, f, indent=2)

        except Exception as e:
            logger.error(f"Error storing processing results: {str(e)}")