import re
import random
import os
from datetime import datetime


def extract_text_from_document(file_path):
    """
    Simulates OCR text extraction.
    In a real system, this would use an OCR library like Tesseract.
    """
    # For simulation, we'll extract data from the filename
    filename = os.path.basename(file_path)

    # Extract common patterns
    extracted_data = {
        'text': f"Extracted content from {filename}",
        'extracted_fields': {}
    }

    # Extract dates (format: YYYY-MM-DD)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if date_match:
        extracted_data['extracted_fields']['date'] = date_match.group(1)

    # Extract business name (format: BusinessName_)
    name_match = re.search(r'([A-Za-z]+)_', filename)
    if name_match:
        extracted_data['extracted_fields']['business_name'] = name_match.group(1)

    # Extract registration numbers (format: REG123456)
    reg_match = re.search(r'(REG\d+)', filename)
    if reg_match:
        extracted_data['extracted_fields']['registration_number'] = reg_match.group(1)

    return extracted_data


def is_valid_document_format(filename, document_type):
    """
    Check if the document filename follows expected patterns for the document type.
    This simulates AI validation based on naming conventions.
    """
    valid_patterns = {
        'dti_sec': r'^(DTI|SEC)_REG\d+_\d{4}-\d{2}-\d{2}',
        'lease': r'^LEASE_\d{4}-\d{2}-\d{2}_\w+',
        'title': r'^TCT\d+_\w+',
        'consent': r'^CONSENT_\w+_\d{4}-\d{2}-\d{2}',
        'signage': r'^SIGNAGE_\w+',
        'fire_cert': r'^FIRE_CERT_\d{4}-\d{2}-\d{2}',
        'zoning': r'^ZONING_\w+',
        'hoa': r'^HOA_PERMIT_\w+',
        'occupancy': r'^OCCUPANCY_\w+',
        'sanitary': r'^SANITARY_\w+_\d{4}',
        'barangay': r'^BRGY_CLEARANCE_\w+',
        'gross_receipt': r'^GROSS_RECEIPT_\d{4}',
        'sale_deed': r'^DEED_SALE_\w+',
        'transfer': r'^TRANSFER_\w+_\d{4}-\d{2}-\d{2}',
        'closure': r'^CLOSURE_\w+_\d{4}-\d{2}-\d{2}',
        'board_resolution': r'^BOARD_RES_\w+_\d{4}-\d{2}-\d{2}',
    }

    if document_type not in valid_patterns:
        return False

    return bool(re.match(valid_patterns[document_type], filename))