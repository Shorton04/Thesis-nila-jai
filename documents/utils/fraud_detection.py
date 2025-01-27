# documents/utils/fraud_detection.py
'''
import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import os
from datetime import datetime
import re


class FraudDetector:
    def __init__(self):
        self.tampering_threshold = 0.7
        self.forgery_threshold = 0.8

    def check_image_manipulation(self, image):
        """Check for signs of image manipulation."""
        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Error Level Analysis (ELA)
        temp_filename = 'temp.jpg'
        cv2.imwrite(temp_filename, image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        saved_image = cv2.imread(temp_filename)
        os.remove(temp_filename)

        difference = cv2.absdiff(image, saved_image)
        ela_score = np.mean(difference) / 255.0

        # Check for copy-paste artifacts
        edges = cv2.Canny(gray, 100, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        suspicious_regions = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                suspicious_regions.append((x, y, w, h))

        return {
            'ela_score': ela_score,
            'suspicious_regions': suspicious_regions
        }

    def check_text_consistency(self, text):
        """Check for inconsistencies in text that might indicate tampering."""
        flags = {
            'inconsistent_fonts': False,
            'misaligned_text': False,
            'suspicious_patterns': False,
            'inconsistent_spacing': False
        }

        # Check for font inconsistencies using OCR confidence
        words_data = pytesseract.image_to_data(text, output_type=pytesseract.Output.DICT)

        # Analyze font consistency
        fonts = set()
        for i, word in enumerate(words_data['text']):
            if word.strip():
                fonts.add(words_data['font'])

        if len(fonts) > 3:  # Threshold for suspicious number of fonts
            flags['inconsistent_fonts'] = True

        # Check for misaligned text
        prev_top = None
        for top in words_data['top']:
            if prev_top is not None:
                if abs(top - prev_top) < 2:  # Threshold for misalignment
                    flags['misaligned_text'] = True
            prev_top = top

        # Check for inconsistent spacing
        word_spaces = []
        prev_right = None
        prev_left = None

        for i in range(len(words_data['text'])):
            if words_data['text'][i].strip():
                left = words_data['left'][i]
                right = left + words_data['width'][i]

                if prev_right is not None:
                    space = left - prev_right
                    word_spaces.append(space)

                prev_right = right
                prev_left = left

        if word_spaces:
            std_dev = np.std(word_spaces)
            if std_dev > 10:  # Threshold for inconsistent spacing
                flags['inconsistent_spacing'] = True

        return flags

    def validate_dates(self, text):
        """Check for suspicious date patterns or inconsistencies."""
        date_flags = {
            'future_dates': False,
            'inconsistent_dates': False,
            'invalid_dates': False
        }

        # Extract dates using regex
        date_patterns = [
            r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
            r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'  # Month DD, YYYY
        ]

        found_dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    date_str = match.group()
                    if '/' in date_str:
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    elif '-' in date_str:
                        date_obj = datetime.strptime(date_str, '%d-%m-%Y')
                    else:
                        date_obj = datetime.strptime(date_str, '%B %d, %Y')
                    found_dates.append(date_obj)
                except ValueError:
                    date_flags['invalid_dates'] = True

        if found_dates:
            # Check for future dates
            current_date = datetime.now()
            for date in found_dates:
                if date > current_date:
                    date_flags['future_dates'] = True

            # Check for date consistency
            if len(found_dates) > 1:
                date_diffs = []
                for i in range(len(found_dates) - 1):
                    diff = abs((found_dates[i] - found_dates[i + 1]).days)
                    date_diffs.append(diff)

                if max(date_diffs) > 365 * 2:  # Suspicious if dates are more than 2 years apart
                    date_flags['inconsistent_dates'] = True

        return date_flags

    def check_signature_authenticity(self, image):
        """Analyze signatures for potential forgery."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        signature_metrics = {
            'continuity_score': 0.0,
            'pressure_variation': 0.0,
            'suspicious': False
        }

        if contours:
            # Analyze continuity
            total_length = sum(cv2.arcLength(cnt, True) for cnt in contours)
            avg_length = total_length / len(contours)

            # Analyze pressure variation
            pressure_points = []
            for cnt in contours:
                mask = np.zeros_like(gray)
                cv2.drawContours(mask, [cnt], -1, 255, -1)
                pressure = cv2.mean(gray, mask=mask)[0]
                pressure_points.append(pressure)

            pressure_variation = np.std(pressure_points) if pressure_points else 0

            signature_metrics['continuity_score'] = avg_length
            signature_metrics['pressure_variation'] = pressure_variation
            signature_metrics['suspicious'] = (pressure_variation < 10 or len(contours) < 3)

        return signature_metrics

    def analyze_document(self, image_path):
        """Main method to analyze a document for potential fraud."""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Could not read image file")

        # Get OCR text
        text = pytesseract.image_to_string(image)

        # Perform all checks
        manipulation_results = self.check_image_manipulation(image)
        text_consistency = self.check_text_consistency(text)
        date_validation = self.validate_dates(text)
        signature_analysis = self.check_signature_authenticity(image)

        # Calculate overall fraud score
        fraud_score = 0.0
        flags = []

        # Check image manipulation
        if manipulation_results['ela_score'] > self.tampering_threshold:
            fraud_score += 0.4
            flags.append("Possible image manipulation detected")

        # Check text consistency
        if any(text_consistency.values()):
            fraud_score += 0.2
            flags.append("Inconsistent text patterns detected")

        # Check dates
        if any(date_validation.values()):
            fraud_score += 0.2
            flags.append("Suspicious date patterns found")

        # Check signature
        if signature_analysis['suspicious']:
            fraud_score += 0.2
            flags.append("Suspicious signature characteristics")

        return {
            'fraud_score': min(fraud_score, 1.0),
            'flags': flags,
            'details': {
                'manipulation_analysis': manipulation_results,
                'text_consistency': text_consistency,
                'date_validation': date_validation,
                'signature_analysis': signature_analysis
            }
        }
'''