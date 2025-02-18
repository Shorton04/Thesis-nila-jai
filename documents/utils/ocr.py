# documents/utils/ocr.py
import pytesseract
from PIL import Image
import cv2
import numpy as np
from pdf2image import convert_from_bytes
import io
from typing import Dict


class ImagePreprocessor:
    """Handles image preprocessing for better OCR results."""

    @staticmethod
    def enhance_for_ocr(image: Image.Image) -> Image.Image:
        """
        Enhance image quality for better OCR results.
        Args:
            image: PIL Image object
        Returns:
            Enhanced PIL Image
        """
        try:
            # Convert PIL Image to OpenCV format
            np_image = np.array(image)

            # Convert to grayscale if needed
            if len(np_image.shape) == 3:
                gray = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = np_image

            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )

            # Noise removal
            denoised = cv2.fastNlMeansDenoising(thresh)

            # Convert back to PIL Image
            enhanced_image = Image.fromarray(denoised)

            return enhanced_image

        except Exception as e:
            print(f"Image Enhancement Error: {str(e)}")
            return image  # Return original image if enhancement fails


class OCRProcessor:
    """Handles OCR processing for documents."""

    @staticmethod
    def process_image(image_bytes: bytes) -> Dict:
        """
        Extract text from image bytes.
        Args:
            image_bytes: Image file in bytes
        Returns:
            Dictionary with OCR results
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to grayscale if needed
            if image.mode != 'L':
                image = image.convert('L')

            # Enhance image
            enhanced_image = ImagePreprocessor.enhance_for_ocr(image)

            # Perform OCR
            text = pytesseract.image_to_string(enhanced_image)

            # Get confidence scores
            data = pytesseract.image_to_data(enhanced_image, output_type=pytesseract.Output.DICT)
            confidence_scores = [conf for conf in data['conf'] if conf != -1]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

            return {
                'success': True,
                'full_text': text.strip(),
                'confidence': avg_confidence,
                'word_count': len(text.split()),
                'details': {
                    'confidence_scores': confidence_scores,
                    'words': data['text']
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def process_pdf(pdf_bytes: bytes) -> Dict:
        """
        Extract text from PDF bytes.
        Args:
            pdf_bytes: PDF file in bytes
        Returns:
            Dictionary with OCR results
        """
        try:
            # Convert PDF to images
            images = convert_from_bytes(pdf_bytes)

            # Process each page
            pages_text = []
            total_confidence = 0
            word_count = 0

            for i, image in enumerate(images, 1):
                # Process each page as an image
                result = OCRProcessor.process_image(
                    OCRProcessor._pil_to_bytes(image)
                )

                if result['success']:
                    pages_text.append(f"Page {i}:\n{result['full_text']}")
                    total_confidence += result['confidence']
                    word_count += result['word_count']

            # Calculate average confidence across all pages
            avg_confidence = total_confidence / len(images) if images else 0

            return {
                'success': True,
                'full_text': '\n\n'.join(pages_text),
                'confidence': avg_confidence,
                'page_count': len(images),
                'word_count': word_count,
                'details': {
                    'pages': pages_text
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _pil_to_bytes(image: Image.Image) -> bytes:
        """Convert PIL Image to bytes."""
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()