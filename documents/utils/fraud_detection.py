# documents/utils/fraud_detection.py
import cv2
import numpy as np
from typing import Dict, List, Tuple
import io


class FraudDetector:
    """Detects potential document tampering and fraud."""

    @staticmethod
    def analyze_document(image_bytes: bytes) -> Dict:
        """
        Analyze document for potential tampering.
        Returns dictionary with analysis results.
        """
        try:
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

        except Exception as e:
            print(f"Fraud Detection Error: {str(e)}")
            return {
                'tampering_detected': False,
                'confidence_score': 0.0,
                'suspicious_regions': [],
                'error': str(e)
            }

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
            suspicious_mask = cv2.threshold(
                cv2.cvtColor(ela_image, cv2.COLOR_BGR2GRAY),
                threshold, 255, cv2.THRESH_BINARY
            )[1]

            # Find contours of suspicious regions
            contours, _ = cv2.findContours(
                suspicious_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

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
                'score': min(1.0, diff_mean / 50.0),
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

            # Return analysis results
            return {
                'score': min(1.0, noise_mean / 30.0),
                'regions': [],
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

            # Basic clone detection using edge detection
            edges = cv2.Canny(gray, 100, 200)

            # Simple analysis based on edge density
            edge_density = np.mean(edges) / 255.0

            return {
                'score': min(1.0, edge_density),
                'regions': [],
                'details': {
                    'edge_density': float(edge_density)
                }
            }

        except Exception as e:
            return {
                'score': 0.0,
                'regions': [],
                'error': str(e)
            }