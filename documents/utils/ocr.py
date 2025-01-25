# documents/utils/ocr.py
import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
from pdf2image import convert_from_path
import os


class OCRProcessor:
    def __init__(self):
        # Configure Tesseract path if needed
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        self.supported_formats = {'pdf', 'jpg', 'jpeg', 'png'}

    def preprocess_image(self, image):
        """Improve image quality for better OCR results."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply thresholding to preprocess the image
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # Apply dilation to connect text components
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gray = cv2.dilate(gray, kernel, iterations=1)

        # Apply median blur to remove noise
        gray = cv2.medianBlur(gray, 3)

        return gray

    def extract_text_from_image(self, image_path):
        """Extract text from an image file."""
        # Read image using OpenCV
        image = cv2.imread(image_path)

        # Preprocess the image
        processed_image = self.preprocess_image(image)

        # Perform OCR
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed_image, config=custom_config)

        # Get confidence scores
        data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
        confidences = [int(conf) for conf in data['conf'] if conf != '-1']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return text.strip(), avg_confidence / 100

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from a PDF file."""
        # Convert PDF to images
        images = convert_from_path(pdf_path)

        full_text = []
        total_confidence = 0

        # Process each page
        for i, image in enumerate(images):
            # Save image temporarily
            temp_path = f"temp_page_{i}.png"
            image.save(temp_path, 'PNG')

            # Extract text from the page
            text, confidence = self.extract_text_from_image(temp_path)
            full_text.append(text)
            total_confidence += confidence

            # Clean up temporary file
            os.remove(temp_path)

        avg_confidence = total_confidence / len(images) if images else 0
        return '\n'.join(full_text), avg_confidence

    def extract_specific_fields(self, text):
        """Extract specific fields from the extracted text."""
        fields = {
            'registration_number': None,
            'business_name': None,
            'address': None,
            'owner_name': None,
            'contact_number': None,
        }

        # Registration number pattern (e.g., DTI/SEC number)
        reg_pattern = r'(?i)registration(?:\s+no\.?|\s+number)?[\s:]+([A-Z0-9-]+)'
        reg_match = re.search(reg_pattern, text)
        if reg_match:
            fields['registration_number'] = reg_match.group(1)

        # Business name pattern
        business_pattern = r'(?i)business\s+name[\s:]+([^\n]+)'
        business_match = re.search(business_pattern, text)
        if business_match:
            fields['business_name'] = business_match.group(1).strip()

        # Address pattern
        address_pattern = r'(?i)address[\s:]+([^\n]+)'
        address_match = re.search(address_pattern, text)
        if address_match:
            fields['address'] = address_match.group(1).strip()

        # Owner name pattern
        owner_pattern = r'(?i)owner[\s:]+([^\n]+)'
        owner_match = re.search(owner_pattern, text)
        if owner_match:
            fields['owner_name'] = owner_match.group(1).strip()

        # Contact number pattern
        contact_pattern = r'(?i)(?:contact|phone|tel(?:ephone)?)(?:\s+no\.?|\s+number)?[\s:]+([0-9\s+-]+)'
        contact_match = re.search(contact_pattern, text)
        if contact_match:
            fields['contact_number'] = contact_match.group(1).strip()

        return fields

    def process_document(self, file_path):
        """Main method to process a document and extract information."""
        file_extension = file_path.split('.')[-1].lower()

        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_extension}")

        try:
            if file_extension == 'pdf':
                text, confidence = self.extract_text_from_pdf(file_path)
            else:
                text, confidence = self.extract_text_from_image(file_path)

            # Extract specific fields
            fields = self.extract_specific_fields(text)

            return {
                'text': text,
                'confidence': confidence,
                'fields': fields
            }

        except Exception as e:
            raise Exception(f"Error processing document: {str(e)}")