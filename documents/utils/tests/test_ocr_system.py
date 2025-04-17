# documents/utils/tests/test_ocr_system.py
import pytest
from PIL import Image, ImageDraw, ImageFont  # Added ImageDraw import
import pytesseract
from pdf2image import convert_from_path
import os
from pathlib import Path
import io

# Get the current directory
TEST_DIR = Path(__file__).parent
TEST_FILES_DIR = TEST_DIR / 'test_files'


@pytest.fixture(scope="session")
def setup_test_files():
    """Create test files before running tests"""
    # Create test directory if it doesn't exist
    TEST_FILES_DIR.mkdir(parents=True, exist_ok=True)

    # Create test image
    img = Image.new('RGB', (800, 300), color='white')
    d = ImageDraw.Draw(img)
    text = "Test Business Permit\nCompany: ABC Corp"
    d.text((50, 50), text, fill='black')
    img_path = TEST_FILES_DIR / 'test_image.png'
    img.save(img_path)

    # Create test PDF using FPDF
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Test PDF Document", ln=1, align="C")
    pdf_path = TEST_FILES_DIR / 'test_doc.pdf'
    pdf.output(str(pdf_path))

    yield {
        'image_path': img_path,
        'pdf_path': pdf_path
    }

    # Cleanup after tests
    if img_path.exists():
        img_path.unlink()
    if pdf_path.exists():
        pdf_path.unlink()


def test_tesseract_installation():
    """Test if Tesseract is installed and accessible"""
    try:
        version = pytesseract.get_tesseract_version()
        # Fixed version comparison
        assert str(version) >= "4.0", "Tesseract version should be 4.0 or higher"
    except Exception as e:
        pytest.fail(f"Tesseract not properly installed: {str(e)}")


def test_poppler_installation():
    """Test if Poppler is installed and accessible"""
    try:
        # Create a small test PDF and try to convert it
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Test", ln=1, align="C")

        # Save PDF to temporary file
        temp_pdf = TEST_FILES_DIR / 'temp_test.pdf'
        pdf.output(str(temp_pdf))

        # Try to convert the PDF to images
        images = convert_from_path(str(temp_pdf))
        assert len(images) > 0, "Should be able to convert PDF to images"

        # Cleanup
        if temp_pdf.exists():
            temp_pdf.unlink()
    except Exception as e:
        pytest.fail(f"Poppler not properly installed: {str(e)}")


def test_image_ocr(setup_test_files):
    """Test OCR on image file"""
    image_path = setup_test_files['image_path']
    try:
        # Perform OCR on test image
        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img)

        assert "Test Business Permit" in text, "Should detect text from image"
        assert "ABC Corp" in text, "Should detect company name from image"
    except Exception as e:
        pytest.fail(f"Image OCR failed: {str(e)}")


def test_pdf_processing(setup_test_files):
    """Test PDF processing and OCR"""
    pdf_path = setup_test_files['pdf_path']
    try:
        # Convert PDF to images
        images = convert_from_path(str(pdf_path))
        assert len(images) > 0, "Should convert PDF to at least one image"

        # Perform OCR on first page
        text = pytesseract.image_to_string(images[0])
        assert "Test PDF Document" in text, "Should detect text from PDF"
    except Exception as e:
        pytest.fail(f"PDF processing failed: {str(e)}")


def test_ocr_accuracy():
    """Test OCR accuracy with known text"""
    # Create a high-quality test image
    width = 800
    height = 200
    background_color = 'white'
    text_color = 'black'
    test_text = "OCR ACCURACY TEST 12345"

    # Create new image with white background
    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img)

    try:
        # Try to load Arial font
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        try:
            # Try to load DejaVu Sans
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            # Fallback to default font
            font = None

    # Calculate text position for centering
    if font:
        text_bbox = draw.textbbox((0, 0), test_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw.text((x, y), test_text, font=font, fill=text_color)
    else:
        draw.text((width // 4, height // 3), test_text, fill=text_color)

    # Configure Tesseract
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '

    # Perform OCR
    text = pytesseract.image_to_string(
        img,
        config=custom_config
    ).strip()

    # Normalize strings by removing spaces and comparing
    expected_normalized = ''.join(test_text.split())
    actual_normalized = ''.join(text.split())

    # Compare results
    assert expected_normalized == actual_normalized, (
        f"\nOCR accuracy test failed!"
        f"\nExpected (original): '{test_text}'"
        f"\nGot (original):      '{text}'"
        f"\nExpected (normalized): '{expected_normalized}'"
        f"\nGot (normalized):      '{actual_normalized}'"
        f"\nLength: {len(actual_normalized)} (expected {len(expected_normalized)})"
        f"\nMatching: {sum(1 for a, b in zip(expected_normalized, actual_normalized) if a == b)} "
        f"of {len(expected_normalized)} characters"
    )


def test_error_handling():
    """Test error handling for invalid inputs"""
    # Test with empty image
    img = Image.new('RGB', (100, 100), color='white')
    text = pytesseract.image_to_string(img)
    assert text.strip() == "", "Empty image should return empty string"

    # Test with invalid file path
    with pytest.raises(Exception):
        convert_from_path("nonexistent.pdf")