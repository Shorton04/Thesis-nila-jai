# documents/utils/tests/test_simple_fraud.py
import pytest
import numpy as np
import cv2
from PIL import Image


def test_basic_tampering():
    """Basic test for image tampering detection"""
    try:
        # Create original image
        img = Image.new('RGB', (800, 400), 'white')
        img_np = np.array(img)

        # Create tampered version
        tampered = img_np.copy()
        cv2.rectangle(tampered, (200, 100), (400, 300), (0, 0, 0), -1)

        # Basic difference check
        diff = cv2.absdiff(img_np, tampered)
        diff_score = np.mean(diff)

        assert diff_score > 0, "Should detect tampering"

    except Exception as e:
        pytest.fail(f"Basic tampering test failed: {str(e)}")