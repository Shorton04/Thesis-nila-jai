try:
    # Test Tesseract
    import pytesseract

    print("✓ Tesseract is installed")
    print(f"Tesseract version: {pytesseract.get_tesseract_version()}")

    # Test Poppler
    from pdf2image import convert_from_path

    print("✓ Poppler/pdf2image is installed")

    # Test PIL
    from PIL import Image

    print("✓ PIL/Pillow is installed")

    print("\nAll OCR dependencies are installed successfully!")

except ImportError as e:
    print(f"⨯ Import Error: {str(e)}")
except Exception as e:
    print(f"⨯ Error: {str(e)}")