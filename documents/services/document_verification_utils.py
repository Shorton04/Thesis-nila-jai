import os
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_extension(file):
    """
    Validates that the uploaded file has an allowed extension.
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        allowed_exts = ', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)
        raise ValidationError(f'Unsupported file extension. Allowed extensions are: {allowed_exts}')


def get_document_requirements(application_type):
    """
    Return required document types based on application type.
    """
    requirements = {
        'new': [
            'dti_sec',
            'lease',
            'signage',
            'fire_cert',
            'zoning',
            'hoa',
            'occupancy',
            'sanitary',
            'barangay',
        ],
        'renewal': [
            'gross_receipt',
        ],
        'amendment': [
            'dti_sec',
            'board_resolution',
            'transfer',
        ],
        'closure': [
            'gross_receipt',
            'barangay',
            'closure',
        ],
    }

    return requirements.get(application_type, [])


def get_document_naming_pattern(doc_type):
    """
    Return the expected naming pattern for a document type.
    Used for displaying guidance to users.
    """
    patterns = {
        'dti_sec': 'DTI_REG123456_YYYY-MM-DD.pdf or SEC_REG123456_YYYY-MM-DD.pdf',
        'lease': 'LEASE_YYYY-MM-DD_BusinessName.pdf',
        'title': 'TCT123456_BusinessName.pdf',
        'consent': 'CONSENT_BusinessName_YYYY-MM-DD.pdf',
        'signage': 'SIGNAGE_BusinessName.jpg',
        'fire_cert': 'FIRE_CERT_YYYY-MM-DD.pdf',
        'zoning': 'ZONING_BusinessName.pdf',
        'hoa': 'HOA_PERMIT_BusinessName.pdf',
        'occupancy': 'OCCUPANCY_BusinessName.pdf',
        'sanitary': 'SANITARY_BusinessName_YYYY.pdf',
        'barangay': 'BRGY_CLEARANCE_BusinessName.pdf',
        'gross_receipt': 'GROSS_RECEIPT_YYYY.pdf',
        'sale_deed': 'DEED_SALE_BusinessName.pdf',
        'transfer': 'TRANSFER_BusinessName_YYYY-MM-DD.pdf',
        'closure': 'CLOSURE_BusinessName_YYYY-MM-DD.pdf',
        'board_resolution': 'BOARD_RES_BusinessName_YYYY-MM-DD.pdf',
    }

    return patterns.get(doc_type, 'Follow the proper naming convention for this document type.')


def check_document_completeness(application):
    """
    Check if all required documents are uploaded for an application.
    Returns a tuple (is_complete, missing_documents)
    """
    required_docs = get_document_requirements(application.application_type)
    submitted_docs = application.documents.values_list('document_type', flat=True)

    # Check which required documents are missing
    missing_docs = []
    for doc_type in required_docs:
        if doc_type not in submitted_docs:
            missing_docs.append(doc_type)

    is_complete = len(missing_docs) == 0

    return is_complete, missing_docs