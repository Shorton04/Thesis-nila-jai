import random
import os
from datetime import datetime
from .ocr import is_valid_document_format


def detect_fraud(file_path, document_type):
    """
    Simulates AI fraud detection by checking filename patterns.
    In a real system, this would use ML/AI to detect tampered documents.
    """
    filename = os.path.basename(file_path)

    # Check if the filename matches the expected pattern for document type
    is_valid = is_valid_document_format(filename, document_type)

    # Generate "AI" verification results
    result = {
        'timestamp': datetime.now().isoformat(),
        'filename': filename,
        'document_type': document_type,
        'is_valid': is_valid,
        'confidence_score': random.uniform(0.75, 0.99) if is_valid else random.uniform(0.1, 0.5),
        'fraud_probability': random.uniform(0.01, 0.1) if is_valid else random.uniform(0.7, 0.95),
    }

    # If fraud is detected, add information about suspicious areas
    if not is_valid:
        result['fraud_areas'] = generate_fake_fraud_areas()
        result['fraud_indicators'] = [
            "Document name pattern doesn't match expected format",
            "Suspicious file structure detected",
            "Potential digital manipulation detected"
        ]
    else:
        result['fraud_areas'] = None

    return result


def generate_fake_fraud_areas():
    """
    Generate fake coordinates for highlighting fraud areas in the document.
    These would be used in the frontend to show highlighted areas.
    """
    # Generate 1-3 suspicious areas with coordinates (x, y, width, height)
    # x and y are percentages of the document width/height (0-100)
    num_areas = random.randint(1, 3)
    areas = []

    for _ in range(num_areas):
        x = random.randint(10, 90)
        y = random.randint(10, 90)
        width = random.randint(5, 15)
        height = random.randint(5, 15)

        # Ensure the area doesn't go outside the document
        if x + width > 100:
            width = 100 - x
        if y + height > 100:
            height = 100 - y

        areas.append({
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'confidence': random.uniform(0.7, 0.95)
        })

    return areas