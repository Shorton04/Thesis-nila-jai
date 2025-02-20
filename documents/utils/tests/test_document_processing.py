# documents/utils/tests/test_document_processing.py
import pytest
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import os
from pathlib import Path
import io

# Get the test directory
TEST_DIR = Path(__file__).parent
TEST_FILES_DIR = TEST_DIR / 'test_files'


@pytest.fixture(scope="session")
def setup_test_documents():
    """Setup test documents directory with sample files"""
    # Create test directory if it doesn't exist
    TEST_FILES_DIR.mkdir(parents=True, exist_ok=True)

    # Create paths for different document types
    files = {
        'dti': TEST_FILES_DIR / 'dti_registration.pdf',
        'barangay': TEST_FILES_DIR / 'barangay_clearance.pdf',
        'tax': TEST_FILES_DIR / 'real_property_tax.pdf',
        'valid_id': TEST_FILES_DIR / 'valid_id.jpeg',
        'zoning': TEST_FILES_DIR / 'zoning_permit.pdf',
        'sanitary': TEST_FILES_DIR / 'sanitary_permit.pdf'
    }

    yield files


def test_dti_registration(setup_test_documents):
    """Test DTI registration document processing"""
    dti_path = setup_test_documents['dti']

    if not dti_path.exists():
        pytest.skip(f"Test file not found: {dti_path}")

    try:
        images = convert_from_path(str(dti_path))
        text = pytesseract.image_to_string(images[0])

        # Updated expected fields based on actual DTI document
        expected_fields = [
            'Business Name No',  # Instead of Registration Number
            'BUMPZ AUTO ACCESSORIES SHOP',  # Actual business name
            'HERYNZ LIWANAG BRUNO',  # Owner name
            'Certificate of Business Name Registration'
        ]

        for field in expected_fields:
            assert field.lower() in text.lower(), f"Could not find {field} in DTI document"

    except Exception as e:
        pytest.fail(f"DTI document processing failed: {str(e)}")


def test_barangay_clearance(setup_test_documents):
    """Test barangay clearance document processing"""
    clearance_path = setup_test_documents['barangay']

    if not clearance_path.exists():
        pytest.skip(f"Test file not found: {clearance_path}")

    try:
        images = convert_from_path(str(clearance_path))
        text = pytesseract.image_to_string(images[0])

        # Updated expected fields based on actual Barangay document
        expected_fields = [
            'Barangay Clearance for Business Permit',
            'Business Trade Name',  # Instead of Business Name
            'Location/Address of Business',
            'BUMPZ AUTO ACCESSORIES SHOP'
        ]

        for field in expected_fields:
            assert field.lower() in text.lower(), f"Could not find {field} in clearance"

    except Exception as e:
        pytest.fail(f"Barangay clearance processing failed: {str(e)}")


def test_real_property_tax(setup_test_documents):
    """Test real property tax document processing"""
    tax_path = setup_test_documents['tax']

    if not tax_path.exists():
        pytest.skip(f"Test file not found: {tax_path}")

    try:
        images = convert_from_path(str(tax_path))
        text = pytesseract.image_to_string(images[0])

        # Updated expected fields based on actual tax document
        expected_fields = [
            'Location',
            'Land Owner/Claimant',
            'Area',
            'HERTY BRUNO'  # Owner name
        ]

        for field in expected_fields:
            assert field.lower() in text.lower(), f"Could not find {field} in tax document"

    except Exception as e:
        pytest.fail(f"Real property tax processing failed: {str(e)}")


def test_valid_id(setup_test_documents):
    """Test valid ID document processing"""
    id_path = setup_test_documents['valid_id']

    if not id_path.exists():
        pytest.skip(f"Test file not found: {id_path}")

    try:
        image = Image.open(id_path)
        text = pytesseract.image_to_string(image)

        # Updated expected fields based on actual ID
        expected_fields = [
            'TIN',  # Instead of just 'Name'
            'BIRTH DATE',
            'ISSUE DATE',
            'DEPARTMENT OF FINANCE'
        ]

        for field in expected_fields:
            assert field.lower() in text.lower(), f"Could not find {field} in ID"

    except Exception as e:
        pytest.fail(f"Valid ID processing failed: {str(e)}")


def test_zoning_permit(setup_test_documents):
    """Test zoning permit document processing"""
    permit_path = setup_test_documents['zoning']

    if not permit_path.exists():
        pytest.skip(f"Test file not found: {permit_path}")

    try:
        images = convert_from_path(str(permit_path))
        text = pytesseract.image_to_string(images[0])

        # Updated expected fields based on actual zoning document
        expected_fields = [
            'Application for Zoning Certification',  # Instead of 'Zoning Permit'
            'Brgy. Bulihan',
            'Malolos City',
            'Zoning Administrator'
        ]

        for field in expected_fields:
            assert field.lower() in text.lower(), f"Could not find {field} in zoning permit"

    except Exception as e:
        pytest.fail(f"Zoning permit processing failed: {str(e)}")


def test_sanitary_permit(setup_test_documents):
    """Test sanitary permit document processing"""
    permit_path = setup_test_documents['sanitary']

    if not permit_path.exists():
        pytest.skip(f"Test file not found: {permit_path}")

    try:
        images = convert_from_path(str(permit_path))
        text = pytesseract.image_to_string(images[0])

        # Updated expected fields based on actual sanitary permit
        expected_fields = [
            'Sanitary Permit to Operate',
            'Type of Establishment',  # Instead of Business Name
            'Date of Expiration',
            'City Health Office'
        ]

        for field in expected_fields:
            assert field.lower() in text.lower(), f"Could not find {field} in sanitary permit"

    except Exception as e:
        pytest.fail(f"Sanitary permit processing failed: {str(e)}")