# documents/utils/tests/test_fraud_detection.py
import pytest
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import io


class FraudDetectionTests:
    @staticmethod
    def ela_analysis(image_np):
        """Error Level Analysis"""
        # Save image with specific quality
        _, buffer = cv2.imencode('.jpg', image_np, [cv2.IMWRITE_JPEG_QUALITY, 90])
        # Read back
        temp_image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        # Calculate difference
        ela = cv2.absdiff(image_np, temp_image)
        return np.mean(ela)

    @staticmethod
    def noise_analysis(image_np):
        """Detect inconsistent noise patterns"""
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        noise = cv2.subtract(gray, cv2.GaussianBlur(gray, (3, 3), 0))
        return np.std(noise)

    @staticmethod
    def copy_move_detection(image_np):
        """Detect copy-move forgery"""
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)

        if descriptors is not None:
            # Match descriptors with themselves
            bf = cv2.BFMatcher()
            matches = bf.knnMatch(descriptors, descriptors, k=2)

            # Count duplicates
            duplicate_count = 0
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    if m.queryIdx != m.trainIdx:  # Ignore self-matches
                        duplicate_count += 1

            return duplicate_count
        return 0


def create_test_image(text="Sample Text", size=(800, 400)):
    """Create a test image with text"""
    img = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), text, fill='black')
    return np.array(img)


def test_ela_detection():
    """Test Error Level Analysis detection"""
    try:
        # Create original image
        original = create_test_image()
        original_ela = FraudDetectionTests.ela_analysis(original)

        # Create manipulated image
        manipulated = original.copy()
        cv2.rectangle(manipulated, (200, 100), (400, 300), (255, 255, 255), -1)
        cv2.putText(manipulated, 'Modified', (220, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        manipulated_ela = FraudDetectionTests.ela_analysis(manipulated)

        # Compare scores
        assert abs(original_ela - manipulated_ela) > 1.0, "ELA failed to detect manipulation"

    except Exception as e:
        pytest.fail(f"ELA detection test failed: {str(e)}")


def test_noise_pattern_detection():
    """Test noise pattern analysis"""
    try:
        # Create original image
        original = create_test_image()
        original_noise = FraudDetectionTests.noise_analysis(original)

        # Create image with inconsistent noise
        manipulated = original.copy()
        noise = np.random.normal(0, 25, (100, 100, 3)).astype(np.uint8)
        manipulated[150:250, 150:250] = noise
        manipulated_noise = FraudDetectionTests.noise_analysis(manipulated)

        # Compare noise levels
        assert abs(original_noise - manipulated_noise) > 5.0, "Noise analysis failed to detect manipulation"

    except Exception as e:
        pytest.fail(f"Noise pattern detection test failed: {str(e)}")


def test_copy_move_detection():
    """Test copy-move forgery detection"""
    try:
        # Create original image
        original = create_test_image()
        original_duplicates = FraudDetectionTests.copy_move_detection(original)

        # Create image with copied region
        manipulated = original.copy()
        region = manipulated[50:150, 50:150].copy()
        manipulated[200:300, 200:300] = region
        manipulated_duplicates = FraudDetectionTests.copy_move_detection(manipulated)

        # Compare duplicate counts
        assert manipulated_duplicates > original_duplicates, "Copy-move detection failed"

    except Exception as e:
        pytest.fail(f"Copy-move detection test failed: {str(e)}")


def test_metadata_consistency():
    """Test metadata consistency checks"""
    try:
        # Create image with metadata
        img = Image.new('RGB', (800, 400), 'white')
        metadata = {
            'Author': 'Test',
            'Creation Time': '2024-02-23 10:00:00'
        }

        # Save image with metadata
        output = io.BytesIO()
        img.save(output, format='PNG', pnginfo=metadata)

        # Check if metadata is preserved
        loaded_img = Image.open(io.BytesIO(output.getvalue()))
        assert hasattr(loaded_img, 'info'), "Metadata not preserved"

    except Exception as e:
        pytest.fail(f"Metadata consistency test failed: {str(e)}")


def test_resolution_tampering():
    """Test resolution tampering detection"""
    try:
        # Create high-res image
        original = create_test_image(size=(2000, 1000))

        # Create down-scaled then up-scaled image
        small = cv2.resize(original, (500, 250))
        manipulated = cv2.resize(small, (2000, 1000))

        # Compare image quality
        original_laplacian = cv2.Laplacian(original, cv2.CV_64F).var()
        manipulated_laplacian = cv2.Laplacian(manipulated, cv2.CV_64F).var()

        assert original_laplacian > manipulated_laplacian, "Resolution tampering detection failed"

    except Exception as e:
        pytest.fail(f"Resolution tampering test failed: {str(e)}")


def test_compression_artifacts():
    """Test detection of multiple compression artifacts"""
    try:
        # Create original image
        original = create_test_image()

        # Save and load multiple times to create compression artifacts
        compressed = original.copy()
        for _ in range(5):
            _, buffer = cv2.imencode('.jpg', compressed, [cv2.IMWRITE_JPEG_QUALITY, 50])
            compressed = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

        # Compare compression levels
        original_compression = FraudDetectionTests.ela_analysis(original)
        multiple_compression = FraudDetectionTests.ela_analysis(compressed)

        assert abs(original_compression - multiple_compression) > 2.0, "Compression artifact detection failed"

    except Exception as e:
        pytest.fail(f"Compression artifact test failed: {str(e)}")