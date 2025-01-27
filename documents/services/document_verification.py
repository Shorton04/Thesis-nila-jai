# documents/services/document_verification.py
'''
import logging
import re
import io
import cv2
import numpy as np
from PIL import Image
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.conf import settings
from django.core.files.base import File
from django.utils import timezone
from ..models import Document, DocumentVersion
from ..utils.ocr import OCRProcessor
from ..utils.fraud_detection import FraudDetector
from ..utils.nlp_validation import NLPValidator

logger = logging.getLogger(__name__)


class DocumentVerificationService:
    """
    Comprehensive service for document verification including OCR processing,
    fraud detection, and content validation.
    """

    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.fraud_detector = FraudDetector()
        self.nlp_validator = NLPValidator()

        # Initialize regex patterns for field extraction
        self.regex_patterns = {
            'registration_number': r'(?i)registration\s+no\.?\s*:\s*([A-Z0-9-]+)',
            'permit_number': r'(?i)permit\s+no\.?\s*:\s*([A-Z0-9-]+)',
            'business_name': r'(?i)business\s+name\s*:\s*([^\n]+)',
            'address': r'(?i)address\s*:\s*([^\n]+)',
            'contact': r'(?i)(?:contact|phone|tel)\s*:\s*([\d\-+]+)',
            'date': r'(?i)date\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            'amount': r'(?i)amount\s*:\s*(?:PHP|₱)?\s*([\d,]+\.?\d*)'
        }

    def verify_document(self, document: Document) -> Dict[str, Any]:
        """
        Perform complete document verification process.
        """
        try:
            verification_results = {
                'success': True,
                'document_id': document.id,
                'verification_status': 'pending',
                'ocr_results': None,
                'fraud_detection': None,
                'validation_results': None,
                'issues': [],
                'extracted_data': {},
                'metadata': {}
            }

            # Step 1: Document Quality Check and Enhancement
            document_path = document.file.path
            quality_analysis = self._analyze_document_quality(document_path)

            if quality_analysis['needs_enhancement']:
                enhanced_path = self._enhance_document_quality(document_path)
                working_path = enhanced_path
            else:
                working_path = document_path

            # Step 2: OCR Processing
            ocr_results = self.ocr_processor.process_document(working_path)
            verification_results['ocr_results'] = ocr_results

            if ocr_results['confidence'] < settings.MIN_OCR_CONFIDENCE:
                verification_results['issues'].append(
                    f"Low OCR confidence: {ocr_results['confidence']:.2f}"
                )

            # Step 3: Extract Information
            extracted_data = self._extract_document_information(
                ocr_results,
                document.document_type
            )
            verification_results['extracted_data'] = extracted_data

            # Step 4: Fraud Detection
            fraud_results = self.fraud_detector.analyze_document(working_path)
            verification_results['fraud_detection'] = fraud_results

            if fraud_results['fraud_score'] > settings.FRAUD_DETECTION_THRESHOLD:
                verification_results['issues'].append("Document flagged for potential fraud")
                verification_results['verification_status'] = 'flagged'

            # Step 5: Content Validation
            validation_results = self._validate_document_content(
                extracted_data,
                document.document_type
            )
            verification_results['validation_results'] = validation_results

            if not validation_results['is_valid']:
                verification_results['issues'].extend(validation_results['issues'])

            # Step 6: Metadata Analysis
            metadata = self._analyze_document_metadata(working_path)
            verification_results['metadata'] = metadata

            # Clean up enhanced document if created
            if working_path != document_path:
                os.remove(working_path)

            # Determine final verification status
            verification_results['verification_status'] = self._determine_verification_status(
                verification_results
            )

            # Update document record
            self._update_document_record(document, verification_results)

            return verification_results

        except Exception as e:
            logger.error(f"Document verification error: {str(e)}")
            return {
                'success': False,
                'document_id': document.id,
                'verification_status': 'error',
                'issues': [f"Verification error: {str(e)}"]
            }

    def _analyze_document_quality(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze document quality metrics and determine if enhancement is needed.
        """
        try:
            image = cv2.imread(document_path)
            quality_metrics = {
                'needs_enhancement': False,
                'issues': [],
                'metrics': {}
            }

            # Resolution check
            height, width = image.shape[:2]
            quality_metrics['metrics']['resolution'] = {
                'width': width,
                'height': height
            }

            if width < settings.MIN_DOCUMENT_WIDTH or height < settings.MIN_DOCUMENT_HEIGHT:
                quality_metrics['needs_enhancement'] = True
                quality_metrics['issues'].append("Low resolution")

            # Contrast check
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            contrast = gray.std()
            quality_metrics['metrics']['contrast'] = contrast

            if contrast < settings.MIN_CONTRAST_THRESHOLD:
                quality_metrics['needs_enhancement'] = True
                quality_metrics['issues'].append("Low contrast")

            # Brightness check
            brightness = gray.mean()
            quality_metrics['metrics']['brightness'] = brightness

            if brightness < settings.MIN_BRIGHTNESS_THRESHOLD or brightness > settings.MAX_BRIGHTNESS_THRESHOLD:
                quality_metrics['needs_enhancement'] = True
                quality_metrics['issues'].append("Suboptimal brightness")

            # Blur detection
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            quality_metrics['metrics']['sharpness'] = laplacian_var

            if laplacian_var < settings.MIN_SHARPNESS_THRESHOLD:
                quality_metrics['needs_enhancement'] = True
                quality_metrics['issues'].append("Image blur detected")

            return quality_metrics

        except Exception as e:
            logger.error(f"Quality analysis error: {str(e)}")
            return {
                'needs_enhancement': False,
                'issues': [f"Quality analysis failed: {str(e)}"],
                'metrics': {}
            }

    def _enhance_document_quality(self, document_path: str) -> str:
        """
        Enhance document quality for better processing results.
        """
        try:
            image = cv2.imread(document_path)
            enhanced_path = f"{os.path.splitext(document_path)[0]}_enhanced.jpg"

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
            cv2.imwrite(enhanced_path, enhanced)

            return enhanced_path

        except Exception as e:
            logger.error(f"Document enhancement error: {str(e)}")
            return document_path

    def _extract_document_information(self, ocr_results: Dict[str, Any],
                                      document_type: str) -> Dict[str, Any]:
        """
        Extract relevant information based on document type.
        """
        extracted_data = {}

        try:
            text = ocr_results.get('text', '')

            if document_type == 'dti_sec_registration':
                extracted_data.update(self._extract_registration_info(text))
            elif document_type == 'business_permit':
                extracted_data.update(self._extract_permit_info(text))
            elif document_type == 'lease_contract':
                extracted_data.update(self._extract_lease_info(text))

            # Extract common fields
            common_fields = self._extract_common_fields(text)
            extracted_data.update(common_fields)

            return extracted_data

        except Exception as e:
            logger.error(f"Information extraction error: {str(e)}")
            return {}

    def _extract_registration_info(self, text: str) -> Dict[str, Any]:
        """
        Extract information specific to registration documents.
        """
        registration_data = {}

        # Registration number
        reg_match = re.search(r'(?i)registration\s+no\.?\s*:\s*([A-Z0-9-]+)', text)
        if reg_match:
            registration_data['registration_number'] = reg_match.group(1)

        # Registration date
        date_match = re.search(r'(?i)date\s+(?:of\s+)?registration\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})', text)
        if date_match:
            registration_data['registration_date'] = date_match.group(1)

        # Business type
        type_match = re.search(r'(?i)type\s+of\s+business\s*:\s*([^\n]+)', text)
        if type_match:
            registration_data['business_type'] = type_match.group(1)

        return registration_data

    def _extract_permit_info(self, text: str) -> Dict[str, Any]:
        """
        Extract information specific to business permits.
        """
        permit_data = {}

        # Permit number
        permit_match = re.search(r'(?i)permit\s+no\.?\s*:\s*([A-Z0-9-]+)', text)
        if permit_match:
            permit_data['permit_number'] = permit_match.group(1)

        # Validity period
        validity_match = re.search(r'(?i)valid\s+(?:until|thru)\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})', text)
        if validity_match:
            permit_data['validity_date'] = validity_match.group(1)

        # Business activity
        activity_match = re.search(r'(?i)business\s+activity\s*:\s*([^\n]+)', text)
        if activity_match:
            permit_data['business_activity'] = activity_match.group(1)

        return permit_data

    def _extract_lease_info(self, text: str) -> Dict[str, Any]:
        """
        Extract information specific to lease contracts.
        """
        lease_data = {}

        # Lease term
        term_match = re.search(r'(?i)lease\s+term\s*:\s*(\d+)\s*(?:year|month)s?', text)
        if term_match:
            lease_data['lease_term'] = term_match.group(1)

        # Monthly rent
        rent_match = re.search(r'(?i)monthly\s+rent\s*:\s*(?:PHP|₱)?\s*([\d,]+\.?\d*)', text)
        if rent_match:
            lease_data['monthly_rent'] = rent_match.group(1)

        # Property address
        address_match = re.search(r'(?i)property\s+address\s*:\s*([^\n]+)', text)
        if address_match:
            lease_data['property_address'] = address_match.group(1)

        return lease_data

    def _extract_common_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract common fields present in most documents.
        """
        common_data = {}

        # Business name
        business_match = re.search(r'(?i)business\s+name\s*:\s*([^\n]+)', text)
        if business_match:
            common_data['business_name'] = business_match.group(1)

        # Address
        address_match = re.search(r'(?i)address\s*:\s*([^\n]+)', text)
        if address_match:
            common_data['address'] = address_match.group(1)

        # Contact information
        contact_match = re.search(r'(?i)(?:contact|phone|tel)\s*:\s*([\d\-+]+)', text)
        if contact_match:
            common_data['contact_number'] = contact_match.group(1)

        return common_data

    def _validate_document_content(self, extracted_data: Dict[str, Any],
                                   document_type: str) -> Dict[str, Any]:
        """
        Validate extracted content based on document type.
        """
        validation_results = {
            'is_valid': True,
            'issues': [],
            'field_validations': {}
        }

        # Get required fields for document type
        required_fields = self._get_required_fields(document_type)

        # Check for missing required fields
        missing_fields = [
            field for field in required_fields
            if not extracted_data.get(field)
        ]

        if missing_fields:
            validation_results['is_valid'] = False
            validation_results['issues'].append(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Validate each field
        for field, value in extracted_data.items():
            field_validation = self._validate_field(field, value, document_type)
            validation_results['field_validations'][field] = field_validation

            if not field_validation['is_valid']:
                validation_results['is_valid'] = False
                validation_results['issues'].extend(field_validation['issues'])

        return validation_results

    def _get_required_fields(self, document_type: str) -> List[str]:
        """
        Get list of required fields based on document type.
        """
        required_fields = {
            'dti_sec_registration': [
                'registration_number',
                'registration_date',
                'business_name'
            ],
            'business_permit': [
                'permit_number',
                'validity_date',
                'business_name',
                'business_activity'
            ],
            'lease_contract': [
                'lease_term',
                'monthly_rent',
                'property_address'
            ]
        }

        return required_fields.get(document_type, [])

    def _validate_field(self, field: str, value: Any,
                        document_type: str) -> Dict[str, Any]:
        """
        Validate individual field based on field type and requirements.
        """
        validation = {
            'is_valid': True,
            'issues': []
        }

        if field == 'registration_number':
            validation = self.nlp_validator.validate_registration_number(value)
        elif field == 'business_name':
            validation = self.nlp_validator.validate_business_name(value)
        elif field in ['address', 'property_address']:
            validation = self.nlp_validator.validate_address(value)
        elif field == 'contact_number':
            validation = self.nlp_validator.validate_contact_number(value)
        elif field == 'monthly_rent':
            validation = self._validate_amount(value)
        elif field.endswith('_date'):
            validation = self._validate_date(value)

        return validation

    # documents/services/document_verification.py (continued)

    def _validate_amount(self, amount: str) -> Dict[str, Any]:
        """
        Validate monetary amounts.
        """
        validation = {
            'is_valid': True,
            'issues': []
        }

        try:
            # Remove currency symbols and commas
            clean_amount = amount.replace('₱', '').replace('PHP', '').replace(',', '').strip()

            # Convert to float
            amount_value = float(clean_amount)

            # Check for negative values
            if amount_value < 0:
                validation['is_valid'] = False
                validation['issues'].append("Amount cannot be negative")

            # Check for reasonable maximum
            if amount_value > settings.MAX_REASONABLE_AMOUNT:
                validation['issues'].append("Amount exceeds reasonable maximum - please verify")

        except ValueError:
            validation['is_valid'] = False
            validation['issues'].append("Invalid amount format")

        return validation

    def _validate_date(self, date_str: str) -> Dict[str, Any]:
        """
        Validate date fields.
        """
        validation = {
            'is_valid': True,
            'issues': []
        }

        try:
            # Try multiple date formats
            date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']
            parsed_date = None

            for date_format in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, date_format).date()
                    break
                except ValueError:
                    continue

            if not parsed_date:
                validation['is_valid'] = False
                validation['issues'].append("Invalid date format")
                return validation

            # Check if date is in future
            if parsed_date > timezone.now().date():
                validation['issues'].append("Future date detected - please verify")

            # Check if date is too old
            min_date = timezone.now().date().replace(year=timezone.now().year - 100)
            if parsed_date < min_date:
                validation['is_valid'] = False
                validation['issues'].append("Date is unreasonably old")

        except Exception:
            validation['is_valid'] = False
            validation['issues'].append("Invalid date")

        return validation

    def _analyze_document_metadata(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze document metadata for additional verification.
        """
        try:
            metadata = {
                'file_info': {},
                'image_metadata': {},
                'creation_info': {},
                'modifications': []
            }

            # Get basic file information
            file_stat = os.stat(document_path)
            metadata['file_info'] = {
                'size': file_stat.st_size,
                'created': datetime.fromtimestamp(file_stat.st_ctime),
                'modified': datetime.fromtimestamp(file_stat.st_mtime),
                'accessed': datetime.fromtimestamp(file_stat.st_atime)
            }

            # Extract image metadata if applicable
            try:
                with Image.open(document_path) as img:
                    metadata['image_metadata'] = {
                        'format': img.format,
                        'mode': img.mode,
                        'size': img.size,
                        'exif': img._getexif() if hasattr(img, '_getexif') else None
                    }
            except Exception:
                pass  # Not an image or no metadata available

            # Check for digital signatures or modifications
            try:
                with open(document_path, 'rb') as f:
                    content = f.read()
                    # Check for common modification markers
                    metadata['modifications'] = self._detect_modifications(content)
            except Exception:
                pass

            return metadata

        except Exception as e:
            logger.error(f"Metadata analysis error: {str(e)}")
            return {}

    def _detect_modifications(self, content: bytes) -> List[Dict[str, Any]]:
        """
        Detect potential document modifications.
        """
        modifications = []

        # Check for PDF modifications
        if content.startswith(b'%PDF'):
            modifications.extend(self._check_pdf_modifications(content))

        # Check for image modifications
        elif any(content.startswith(sig) for sig in [b'\xFF\xD8\xFF', b'\x89PNG', b'GIF']):
            modifications.extend(self._check_image_modifications(content))

        return modifications

    def _check_pdf_modifications(self, content: bytes) -> List[Dict[str, Any]]:
        """
        Check for modifications in PDF documents.
        """
        modifications = []

        # Look for revision markers
        revision_count = content.count(b'/Prev')
        if revision_count > 0:
            modifications.append({
                'type': 'pdf_revision',
                'count': revision_count,
                'severity': 'medium' if revision_count > 3 else 'low'
            })

        # Check for digital signatures
        if b'/SigningTime' in content:
            modifications.append({
                'type': 'digital_signature',
                'severity': 'low',
                'description': 'Document contains digital signatures'
            })

        return modifications

    def _check_image_modifications(self, content: bytes) -> List[Dict[str, Any]]:
        """
        Check for modifications in image files.
        """
        modifications = []

        try:
            # Convert bytes to numpy array for image processing
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Error Level Analysis (ELA)
            ela_score = self._perform_ela(img)
            if ela_score > settings.ELA_THRESHOLD:
                modifications.append({
                    'type': 'image_manipulation',
                    'severity': 'high',
                    'score': ela_score,
                    'description': 'Potential image manipulation detected'
                })

            # Check metadata consistency
            metadata_issues = self._check_metadata_consistency(content)
            modifications.extend(metadata_issues)

        except Exception as e:
            logger.error(f"Image modification check error: {str(e)}")

        return modifications

    def _perform_ela(self, image: np.ndarray) -> float:
        """
        Perform Error Level Analysis on image.
        """
        try:
            # Save image with specific quality
            temp_path = 'temp_ela.jpg'
            cv2.imwrite(temp_path, image, [cv2.IMWRITE_JPEG_QUALITY, 90])

            # Read back the saved image
            saved_image = cv2.imread(temp_path)

            # Calculate difference
            diff = cv2.absdiff(image, saved_image)
            ela_score = np.mean(diff)

            # Clean up
            os.remove(temp_path)

            return ela_score

        except Exception as e:
            logger.error(f"ELA analysis error: {str(e)}")
            return 0.0

    def _check_metadata_consistency(self, content: bytes) -> List[Dict[str, Any]]:
        """
        Check image metadata for consistency and potential tampering.
        """
        issues = []

        try:
            image = Image.open(io.BytesIO(content))
            exif_data = image._getexif() if hasattr(image, '_getexif') else None

            if exif_data:
                # Check software used
                if 306 in exif_data:  # DateTime tag
                    creation_time = exif_data[306]
                    if 'photoshop' in creation_time.lower():
                        issues.append({
                            'type': 'metadata_edited',
                            'severity': 'medium',
                            'description': 'Image edited with photo editing software'
                        })

                # Check for inconsistent timestamps
                timestamp_tags = [306, 36867, 36868]  # Various time-related tags
                timestamps = []

                for tag in timestamp_tags:
                    if tag in exif_data:
                        timestamps.append(exif_data[tag])

                if len(set(timestamps)) > 1:
                    issues.append({
                        'type': 'inconsistent_timestamps',
                        'severity': 'high',
                        'description': 'Inconsistent creation timestamps detected'
                    })

        except Exception as e:
            logger.error(f"Metadata consistency check error: {str(e)}")

        return issues

    def _determine_verification_status(self, results: Dict[str, Any]) -> str:
        """
        Determine final verification status based on all checks.
        """
        if results.get('fraud_detection', {}).get('fraud_score', 0) > settings.FRAUD_DETECTION_THRESHOLD:
            return 'flagged'

        if len(results.get('issues', [])) > settings.MAX_ALLOWED_ISSUES:
            return 'rejected'

        if not results.get('validation_results', {}).get('is_valid', False):
            return 'invalid'

        if results.get('ocr_results', {}).get('confidence', 0) < settings.MIN_OCR_CONFIDENCE:
            return 'needs_review'

        return 'verified'

    def _update_document_record(self, document: Document,
                                verification_results: Dict[str, Any]) -> None:
        """
        Update document record with verification results.
        """
        try:
            document.verification_status = verification_results['verification_status']
            document.extracted_text = verification_results.get('ocr_results', {}).get('text', '')
            document.confidence_score = verification_results.get('ocr_results', {}).get('confidence', 0)
            document.fraud_score = verification_results.get('fraud_detection', {}).get('fraud_score', 0)
            document.fraud_flags = verification_results.get('fraud_detection', {}).get('flags', [])
            document.validation_results = verification_results.get('validation_results', {})
            document.metadata = verification_results.get('metadata', {})
            document.last_verified = timezone.now()

            document.save()

            # Store verification results for audit
            self._store_verification_results(document, verification_results)

        except Exception as e:
            logger.error(f"Error updating document record: {str(e)}")
            raise

    def _store_verification_results(self, document: Document,
                                    results: Dict[str, Any]) -> None:
        """
        Store verification results for audit purposes.
        """
        try:
            results_dir = os.path.join(settings.MEDIA_ROOT, 'verification_results')
            os.makedirs(results_dir, exist_ok=True)

            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"verification_{document.id}_{timestamp}.json"

            with open(os.path.join(results_dir, filename), 'w') as f:
                json.dump({
                    'document_id': document.id,
                    'timestamp': timestamp,
                    'results': results
                }, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error storing verification results: {str(e)}")
            '''