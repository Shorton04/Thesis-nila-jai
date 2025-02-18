# documents/services/document_verification_utils.py
import cv2
import numpy as np
from PIL import Image
import io
import pytesseract
from pdf2image import convert_from_bytes
import spacy
import re
from typing import Dict, List, Tuple


class ImagePreprocessor:
    """Handles image preprocessing for better OCR results."""

    @staticmethod
    def enhance_for_ocr(image):
        """Enhance image quality for better OCR results."""
        # Convert PIL Image to OpenCV format
        np_image = np.array(image)

        # Convert to grayscale if needed
        if len(np_image.shape) == 3:
            gray = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY)
        else:
            gray = np_image

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Noise removal
        denoised = cv2.fastNlMeansDenoising(thresh)

        # Convert back to PIL Image
        enhanced_image = Image.fromarray(denoised)

        return enhanced_image


class OCRProcessor:
    """Handles OCR processing for documents."""

    @staticmethod
    def process_image(image_bytes: bytes) -> Dict:
        """Process image and extract text with layout information."""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Preprocess image
            preprocessed = ImagePreprocessor.enhance_for_ocr(image)

            # Get OCR data with layout analysis
            ocr_data = pytesseract.image_to_data(preprocessed, output_type=pytesseract.Output.DICT)

            # Extract text with confidence and position
            extracted_data = []
            n_boxes = len(ocr_data['text'])
            for i in range(n_boxes):
                if int(float(ocr_data['conf'][i])) > 60:  # Filter low confidence
                    extracted_data.append({
                        'text': ocr_data['text'][i],
                        'confidence': ocr_data['conf'][i],
                        'position': {
                            'x': ocr_data['left'][i],
                            'y': ocr_data['top'][i],
                            'width': ocr_data['width'][i],
                            'height': ocr_data['height'][i]
                        }
                    })

            return {
                'success': True,
                'data': extracted_data,
                'full_text': ' '.join([d['text'] for d in extracted_data])
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def process_pdf(pdf_bytes: bytes) -> Dict:
        """Process PDF and extract text from all pages."""
        try:
            # Convert PDF to images
            images = convert_from_bytes(pdf_bytes)

            # Process each page
            pages_data = []
            for page_num, image in enumerate(images, 1):
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()

                # Process the page
                page_data = OCRProcessor.process_image(img_byte_arr)
                if page_data['success']:
                    pages_data.append({
                        'page_number': page_num,
                        'content': page_data['data']
                    })

            return {
                'success': True,
                'pages': pages_data,
                'full_text': ' '.join([page['content']['full_text']
                                       for page in pages_data if 'full_text' in page['content']])
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class DocumentValidator:
    """Validates document content and structure."""

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def validate_content(self, text: str, document_type: str) -> Dict:
        """Validate document content based on type."""
        validation_results = {
            'is_valid': False,
            'missing_fields': [],
            'extracted_fields': {},
            'warnings': []
        }

        if document_type == 'dti_registration':
            validation_results.update(self._validate_dti_registration(text))
        elif document_type == 'business_permit':
            validation_results.update(self._validate_business_permit(text))
        elif document_type == 'valid_id':
            validation_results.update(self._validate_valid_id(text))

        return validation_results

    def _validate_dti_registration(self, text: str) -> Dict:
        """Validate DTI registration content."""
        doc = self.nlp(text)

        # Required fields
        required_fields = {
            'registration_number': r'Registration Number:?\s*([A-Z0-9-]+)',
            'business_name': r'Business Name:?\s*([^\n]+)',
            'registration_date': r'Date:?\s*(\d{2}/\d{2}/\d{4})',
            'owner_name': r'Owner:?\s*([^\n]+)'
        }

        extracted_fields = {}
        missing_fields = []

        # Extract and validate each field
        for field, pattern in required_fields.items():
            match = re.search(pattern, text)
            if match:
                extracted_fields[field] = match.group(1).strip()
            else:
                missing_fields.append(field)

        # Additional validations
        warnings = []
        if 'business_name' in extracted_fields:
            # Check for restricted words
            restricted_words = ['bank', 'insurance', 'trust', 'cooperative']
            business_name = extracted_fields['business_name'].lower()
            found_restricted = [word for word in restricted_words if word in business_name]
            if found_restricted:
                warnings.append(f"Business name contains restricted words: {', '.join(found_restricted)}")

        return {
            'is_valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'extracted_fields': extracted_fields,
            'warnings': warnings
        }

    def _validate_business_permit(self, text: str) -> Dict:
        """Validate business permit content."""
        required_fields = {
            'permit_number': r'Permit No\.?:?\s*([A-Z0-9-]+)',
            'business_name': r'Business Name:?\s*([^\n]+)',
            'address': r'Address:?\s*([^\n]+)',
            'owner_name': r'Owner:?\s*([^\n]+)',
            'issue_date': r'Date Issued:?\s*(\d{2}/\d{2}/\d{4})',
            'expiry_date': r'Valid Until:?\s*(\d{2}/\d{2}/\d{4})'
        }

        extracted_fields = {}
        missing_fields = []

        # Extract and validate each field
        for field, pattern in required_fields.items():
            match = re.search(pattern, text)
            if match:
                extracted_fields[field] = match.group(1).strip()
            else:
                missing_fields.append(field)

        # Validate dates if present
        warnings = []
        if 'issue_date' in extracted_fields and 'expiry_date' in extracted_fields:
            try:
                from datetime import datetime
                issue_date = datetime.strptime(extracted_fields['issue_date'], '%m/%d/%Y')
                expiry_date = datetime.strptime(extracted_fields['expiry_date'], '%m/%d/%Y')

                if expiry_date <= issue_date:
                    warnings.append("Expiry date is not after issue date")
            except ValueError:
                warnings.append("Invalid date format")

        return {
            'is_valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'extracted_fields': extracted_fields,
            'warnings': warnings
        }

    def _validate_valid_id(self, text: str) -> Dict:
        """Validate government-issued ID content."""
        doc = self.nlp(text)

        # Look for common ID patterns
        id_patterns = {
            'name': r'Name:?\s*([^\n]+)',
            'id_number': r'(?:No\.|Number):?\s*([A-Z0-9-]+)',
            'birth_date': r'(?:Birth Date|Date of Birth):?\s*(\d{2}/\d{2}/\d{4})',
            'address': r'Address:?\s*([^\n]+)'
        }

        extracted_fields = {}
        missing_fields = []

        # Extract and validate each field
        for field, pattern in id_patterns.items():
            match = re.search(pattern, text)
            if match:
                extracted_fields[field] = match.group(1).strip()
            else:
                missing_fields.append(field)

        # Additional validations
        warnings = []
        if 'birth_date' in extracted_fields:
            try:
                from datetime import datetime
                birth_date = datetime.strptime(extracted_fields['birth_date'], '%m/%d/%Y')
                if birth_date > datetime.now():
                    warnings.append("Invalid birth date")
            except ValueError:
                warnings.append("Invalid date format")

        return {
            'is_valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'extracted_fields': extracted_fields,
            'warnings': warnings
        }


class FraudDetector:
    """Detects potential document tampering and fraud."""

    @staticmethod
    def analyze_document(image_bytes: bytes) -> Dict:
        """Analyze document for potential tampering."""
        # Convert bytes to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        results = {
            'tampering_detected': False,
            'confidence_score': 0.0,
            'suspicious_regions': [],
            'analysis_details': {}
        }

        # Run various fraud detection methods
        ela_results = FraudDetector._error_level_analysis(image)
        noise_results = FraudDetector._noise_analysis(image)
        clone_results = FraudDetector._clone_detection(image)

        # Combine results
        results['confidence_score'] = (
                ela_results['score'] * 0.4 +
                noise_results['score'] * 0.3 +
                clone_results['score'] * 0.3
        )

        results['tampering_detected'] = results['confidence_score'] > 0.7
        results['suspicious_regions'] = (
                ela_results['regions'] +
                noise_results['regions'] +
                clone_results['regions']
        )

        results['analysis_details'] = {
            'ela_analysis': ela_results,
            'noise_analysis': noise_results,
            'clone_detection': clone_results
        }

        return results

    @staticmethod
    def _error_level_analysis(image: np.ndarray) -> Dict:
        """Perform Error Level Analysis."""
        try:
            # Save image at quality level 90
            temp_output = io.BytesIO()
            cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tofile(temp_output)

            # Read back the saved image
            temp_input = io.BytesIO(temp_output.getvalue())
            saved_image = cv2.imdecode(np.frombuffer(temp_input.read(), np.uint8), cv2.IMREAD_COLOR)

            # Calculate difference
            ela_image = cv2.absdiff(image, saved_image)

            # Analyze differences
            diff_mean = np.mean(ela_image)
            diff_std = np.std(ela_image)

            # Find suspicious regions
            threshold = diff_mean + (2 * diff_std)
            suspicious_mask = cv2.threshold(cv2.cvtColor(ela_image, cv2.COLOR_BGR2GRAY),
                                            threshold, 255, cv2.THRESH_BINARY)[1]

            # Find contours of suspicious regions
            contours, _ = cv2.findContours(suspicious_mask,
                                           cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)

            suspicious_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w * h > 100:  # Filter out very small regions
                    suspicious_regions.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h)
                    })

            return {
                'score': min(1.0, diff_mean / 50.0),  # Normalize score
                'regions': suspicious_regions,
                'details': {
                    'mean_difference': float(diff_mean),
                    'std_difference': float(diff_std)
                }
            }

        except Exception as e:
            return {
                'score': 0.0,
                'regions': [],
                'error': str(e)
            }

    @staticmethod
    def _noise_analysis(image: np.ndarray) -> Dict:
        """Analyze image noise patterns."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply noise detection filter
            noise = cv2.subtract(gray, cv2.GaussianBlur(gray, (3, 3), 0))

            # Analyze noise statistics
            noise_mean = np.mean(noise)
            noise_std = np.std(noise)

            # Find regions with unusual noise patterns
            threshold = noise_mean + (2 * noise_std)
            noise_mask = cv2.threshold(noise, threshold, 255, cv2.THRESH_BINARY)[1]

            # Find contours of suspicious regions
            contours, _ = cv2.findContours(noise_mask,
                                           cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)

            suspicious_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w * h > 100:  # Filter out very small regions
                    suspicious_regions.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h)
                    })

            return {
                'score': min(1.0, noise_mean / 30.0),  # Normalize score
                'regions': suspicious_regions,
                'details': {
                    'noise_mean': float(noise_mean),
                    'noise_std': float(noise_std)
                }
            }

        except Exception as e:
            return {
                'score': 0.0,
                'regions': [],
                'error': str(e)
            }

    @staticmethod
    def _clone_detection(image: np.ndarray) -> Dict:
        """Detect potentially cloned regions in the image."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply SIFT detector
            sift = cv2.SIFT_create()

            # Find keypoints and descriptors
            keypoints, descriptors = sift.detectAndCompute(gray, None)

            if descriptors is None:
                return {
                    'score': 0.0,
                    'regions': [],
                    'details': {
                        'matches_found': 0
                    }
                }

            # FLANN parameters
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)

            flann = cv2.FlannBasedMatcher(index_params, search_params)

            # Match descriptors with themselves
            matches = flann.knnMatch(descriptors, descriptors, k=2)

            # Store all the good matches as per Lowe's ratio test
            good_matches = []
            suspicious_regions = []

            for i, (m, n) in enumerate(matches):
                if m.distance < 0.7 * n.distance:  # Ratio test
                    if m.queryIdx != m.trainIdx:  # Exclude self-matches
                        good_matches.append([m])

                        # Get the keypoints for the match
                        query_pt = keypoints[m.queryIdx].pt
                        train_pt = keypoints[m.trainIdx].pt

                        # Create region around matched points
                        region = {
                            'x': int(min(query_pt[0], train_pt[0])),
                            'y': int(min(query_pt[1], train_pt[1])),
                            'width': int(abs(query_pt[0] - train_pt[0])),
                            'height': int(abs(query_pt[1] - train_pt[1]))
                        }
                        suspicious_regions.append(region)

            # Calculate score based on number of good matches
            matches_ratio = len(good_matches) / len(keypoints) if keypoints else 0
            score = min(1.0, matches_ratio * 2)  # Normalize score

            return {
                'score': score,
                'regions': suspicious_regions,
                'details': {
                    'matches_found': len(good_matches),
                    'total_keypoints': len(keypoints)
                }
            }

        except Exception as e:
            return {
                'score': 0.0,
                'regions': [],
                'error': str(e)
            }


class DocumentWorkflow:
    """Manages the document processing and verification workflow."""

    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.validator = DocumentValidator()
        self.fraud_detector = FraudDetector()

    async def process_document(self, file_bytes: bytes, document_type: str) -> Dict:
        """
        Process a document through the complete verification workflow.
        Returns comprehensive results including OCR, validation, and fraud detection.
        """
        try:
            results = {
                'success': False,
                'ocr_results': None,
                'validation_results': None,
                'fraud_detection_results': None,
                'overall_status': 'failed',
                'errors': []
            }

            # Step 1: OCR Processing
            if document_type.lower().endswith('pdf'):
                ocr_results = await self._process_async(
                    self.ocr_processor.process_pdf, file_bytes
                )
            else:
                ocr_results = await self._process_async(
                    self.ocr_processor.process_image, file_bytes
                )

            results['ocr_results'] = ocr_results

            if not ocr_results.get('success'):
                results['errors'].append('OCR processing failed')
                return results

            # Step 2: Document Validation
            validation_results = await self._process_async(
                self.validator.validate_content,
                ocr_results['full_text'],
                document_type
            )

            results['validation_results'] = validation_results

            # Step 3: Fraud Detection (for images only)
            if not document_type.lower().endswith('pdf'):
                fraud_results = await self._process_async(
                    self.fraud_detector.analyze_document,
                    file_bytes
                )
                results['fraud_detection_results'] = fraud_results

            # Determine overall status
            results['success'] = True
            results['overall_status'] = self._determine_overall_status(results)

            return results

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'overall_status': 'failed'
            }

    @staticmethod
    async def _process_async(func, *args, **kwargs):
        """Helper method to process functions asynchronously."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    def _determine_overall_status(self, results: Dict) -> str:
        """Determine the overall status based on all verification results."""
        # Default to rejected
        status = 'rejected'

        try:
            # Check OCR results
            if not results['ocr_results']['success']:
                return 'rejected'

            # Check validation results
            validation = results['validation_results']
            if not validation['is_valid']:
                if len(validation['missing_fields']) > len(validation['extracted_fields']):
                    return 'rejected'
                status = 'needs_review'

            # Check fraud detection results if available
            fraud_results = results.get('fraud_detection_results')
            if fraud_results:
                if fraud_results['tampering_detected']:
                    if fraud_results['confidence_score'] > 0.9:
                        return 'rejected'
                    status = 'needs_review'
                elif fraud_results['confidence_score'] < 0.3:
                    if status != 'needs_review':
                        status = 'accepted'

            # If no fraud detection (e.g., PDF) and validation passed
            if not fraud_results and validation['is_valid']:
                status = 'accepted'

            return status

        except Exception as e:
            print(f"Error determining status: {str(e)}")
            return 'rejected'

