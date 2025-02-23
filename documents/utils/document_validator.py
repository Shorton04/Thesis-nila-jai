# documents/utils/document_validator.py
import cv2
import numpy as np
from PIL import Image
import io


class DocumentValidator:
    """Document validation and fraud detection system"""

    def __init__(self):
        # Validation thresholds based on our tests
        self.thresholds = {
            'ela_score': {'min': 0, 'max': 100},
            'noise_score': {'min': 0, 'max': 50},
            'text_quality': {'min': 50},
            'resolution_score': {'min': 50}
        }

    def validate_document(self, file_bytes):
        """
        Validate document authenticity and quality
        Returns: (is_valid, results, message)
        """
        try:
            # Convert bytes to numpy array
            image_np = self._bytes_to_np_array(file_bytes)

            # Run all checks
            results = self._run_validations(image_np)

            # Check if all validations pass
            is_valid = self._check_thresholds(results)

            message = self._generate_validation_message(results)

            return is_valid, results, message

        except Exception as e:
            return False, None, f"Validation error: {str(e)}"

    def _bytes_to_np_array(self, file_bytes):
        """Convert file bytes to numpy array"""
        image = Image.open(io.BytesIO(file_bytes))
        return np.array(image)

    def _run_validations(self, image_np):
        """Run all validation checks"""
        return {
            'ela_score': self._check_ela(image_np),
            'noise_score': self._check_noise(image_np),
            'text_quality': self._check_text_quality(image_np),
            'resolution_score': self._check_resolution(image_np)
        }

    def _check_ela(self, image_np):
        """Check Error Level Analysis"""
        _, buffer = cv2.imencode('.jpg', image_np, [cv2.IMWRITE_JPEG_QUALITY, 90])
        temp_image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        ela = cv2.absdiff(image_np, temp_image)
        return float(np.mean(ela))

    def _check_noise(self, image_np):
        """Check noise patterns"""
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        noise = cv2.subtract(gray, cv2.GaussianBlur(gray, (3, 3), 0))
        return float(np.std(noise))

    def _check_text_quality(self, image_np):
        """Check text clarity"""
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def _check_resolution(self, image_np):
        """Check image resolution quality"""
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)

        # Combined resolution score
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_intensity = np.sqrt(sobelx ** 2 + sobely ** 2).mean()

        return float((laplacian_var + edge_intensity) / 2)

    def _check_thresholds(self, results):
        """Check if results meet thresholds"""
        checks = [
            results['ela_score'] >= self.thresholds['ela_score']['min'] and
            results['ela_score'] < self.thresholds['ela_score']['max'],

            results['noise_score'] >= self.thresholds['noise_score']['min'] and
            results['noise_score'] < self.thresholds['noise_score']['max'],

            results['text_quality'] >= self.thresholds['text_quality']['min'],
            results['resolution_score'] >= self.thresholds['resolution_score']['min']
        ]
        return all(checks)

    def _generate_validation_message(self, results):
        """Generate detailed validation message"""
        messages = []

        if results['ela_score'] >= self.thresholds['ela_score']['max']:
            messages.append("Document may have been manipulated")

        if results['noise_score'] >= self.thresholds['noise_score']['max']:
            messages.append("Unusual noise patterns detected")

        if results['text_quality'] < self.thresholds['text_quality']['min']:
            messages.append("Text quality is below acceptable level")

        if results['resolution_score'] < self.thresholds['resolution_score']['min']:
            messages.append("Document resolution is too low")

        if not messages:
            return "Document passed all validation checks"

        return " | ".join(messages)

    def determine_quarantine_reason(self, results):
        """Determine if document should be quarantined and why"""
        if results['ela_score'] >= self.thresholds['ela_score']['max']:
            return 'tampering'
        elif results['noise_score'] >= self.thresholds['noise_score']['max']:
            return 'suspicious_noise'
        elif results['text_quality'] < self.thresholds['text_quality']['min']:
            return 'low_quality'
        elif results['resolution_score'] < self.thresholds['resolution_score']['min']:
            return 'resolution'
        return None