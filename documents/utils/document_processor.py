# documents/utils/document_processor.py
'''
from .ocr import OCRProcessor
from .fraud_detection import FraudDetector
from .nlp_validation import NLPValidator
import os
from django.conf import settings
import logging
from datetime import datetime
import json
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        self.ocr = OCRProcessor()
        self.fraud_detector = FraudDetector()
        self.nlp_validator = NLPValidator()

    def extract_form_data(self, document_path):
        """
        Extract data specifically for form auto-fill.
        """
        try:
            # Process document with OCR
            ocr_results = self.ocr.process_document(document_path)

            # Extract specific fields
            extracted_data = {
                'business_name': None,
                'address': None,
                'registration_number': None,
                'owner_name': None,
                'contact_number': None,
                'email': None,
                'business_type': None,
                'registration_date': None
            }

            # Map OCR extracted fields to form fields
            if ocr_results.get('fields'):
                field_mapping = {
                    'business_name': ['business_name', 'business', 'name', 'company_name'],
                    'address': ['address', 'business_address', 'location'],
                    'registration_number': ['registration_number', 'registration_no', 'reg_number', 'dti_number',
                                            'sec_number'],
                    'owner_name': ['owner_name', 'owner', 'proprietor'],
                    'contact_number': ['contact_number', 'telephone', 'phone', 'mobile'],
                    'email': ['email', 'email_address', 'e-mail'],
                    'business_type': ['business_type', 'type_of_business', 'organization_type'],
                    'registration_date': ['registration_date', 'date_registered', 'reg_date']
                }

                for form_field, possible_matches in field_mapping.items():
                    for match in possible_matches:
                        if match in ocr_results['fields']:
                            extracted_data[form_field] = ocr_results['fields'][match]
                            break

            # Validate extracted data
            validated_data = self.validate_extracted_data(extracted_data)

            return {
                'success': True,
                'extracted_data': validated_data,
                'confidence_score': ocr_results.get('confidence', 0)
            }

        except Exception as e:
            logger.error(f"Form data extraction error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'extracted_data': {},
                'confidence_score': 0
            }

    def validate_extracted_data(self, data):
        """
        Validate and clean extracted form data.
        """
        validated_data = data.copy()

        # Validate business name
        if validated_data.get('business_name'):
            name_validation = self.nlp_validator.validate_business_name(validated_data['business_name'])
            if name_validation['is_valid']:
                validated_data['business_name'] = validated_data['business_name'].strip()
            else:
                validated_data['business_name'] = None

        # Validate address
        if validated_data.get('address'):
            address_validation = self.nlp_validator.validate_address(validated_data['address'])
            if address_validation['is_valid']:
                validated_data['address'] = validated_data['address'].strip()
            else:
                validated_data['address'] = None

        # Validate contact number
        if validated_data.get('contact_number'):
            contact_validation = self.nlp_validator.validate_contact_number(validated_data['contact_number'])
            if contact_validation['is_valid']:
                validated_data['contact_number'] = ''.join(filter(str.isdigit, validated_data['contact_number']))
            else:
                validated_data['contact_number'] = None

        # Validate email
        if validated_data.get('email'):
            email_validation = self.nlp_validator.validate_email(validated_data['email'])
            if email_validation['is_valid']:
                validated_data['email'] = validated_data['email'].lower().strip()
            else:
                validated_data['email'] = None

        # Validate registration number
        if validated_data.get('registration_number'):
            reg_validation = self.nlp_validator.validate_registration_number(validated_data['registration_number'])
            if not reg_validation['is_valid']:
                validated_data['registration_number'] = None

        # Validate registration date
        if validated_data.get('registration_date'):
            try:
                # Try to parse the date
                parsed_date = None
                date_formats = [
                    '%Y-%m-%d',
                    '%m/%d/%Y',
                    '%d/%m/%Y',
                    '%B %d, %Y',
                    '%b %d, %Y'
                ]

                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(validated_data['registration_date'], date_format)
                        break
                    except ValueError:
                        continue

                if parsed_date:
                    validated_data['registration_date'] = parsed_date.strftime('%Y-%m-%d')
                else:
                    validated_data['registration_date'] = None
            except Exception:
                validated_data['registration_date'] = None

        return validated_data

    def process_document_batch(self, documents):
        """
        Process multiple documents in batch.
        """
        results = []

        for doc in documents:
            doc_path = doc.get('path')
            doc_type = doc.get('type')

            if not doc_path or not doc_type:
                continue

            result = self.process_document(doc_path, doc_type)
            results.append({
                'document_path': doc_path,
                'document_type': doc_type,
                'processing_results': result
            })

        return results

    def enhance_document_image(self, image_path):
        """
        Enhance document image quality for better OCR results.
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image file")

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)

            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # Save enhanced image
            enhanced_path = image_path.replace('.', '_enhanced.')
            cv2.imwrite(enhanced_path, enhanced)

            return enhanced_path

        except Exception as e:
            logger.error(f"Image enhancement error: {str(e)}")
            return image_path

    def save_processing_results(self, results, output_path):
        """
        Save document processing results to a JSON file.
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Convert datetime objects to string
            def datetime_handler(x):
                if isinstance(x, datetime):
                    return x.isoformat()
                raise TypeError(f"Object of type {type(x)} is not JSON serializable")

            # Save results
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, default=datetime_handler, indent=4)

            return True

        except Exception as e:
            logger.error(f"Error saving processing results: {str(e)}")
            return False

    def analyze_document_quality(self, document_path):
        """
        Analyze document image quality and provide recommendations.
        """
        try:
            image = cv2.imread(document_path)
            if image is None:
                raise ValueError("Could not read image file")

            analysis = {
                'resolution': {'width': image.shape[1], 'height': image.shape[0]},
                'quality_score': 0,
                'issues': [],
                'recommendations': []
            }

            # Check resolution
            min_width = 1000
            min_height = 1000
            if image.shape[1] < min_width or image.shape[0] < min_height:
                analysis['issues'].append("Low resolution")
                analysis['recommendations'].append(
                    f"Recommended minimum resolution: {min_width}x{min_height} pixels"
                )

            # Check brightness
            brightness = np.mean(image)
            if brightness < 100:
                analysis['issues'].append("Image too dark")
                analysis['recommendations'].append("Increase image brightness")
            elif brightness > 200:
                analysis['issues'].append("Image too bright")
                analysis['recommendations'].append("Decrease image brightness")

            # Check contrast
            contrast = np.std(image)
            if contrast < 50:
                analysis['issues'].append("Low contrast")
                analysis['recommendations'].append("Improve image contrast")

            # Calculate quality score
            quality_score = 100
            quality_score -= len(analysis['issues']) * 20
            analysis['quality_score'] = max(0, quality_score)

            return analysis

        except Exception as e:
            logger.error(f"Document quality analysis error: {str(e)}")
            return None
'''