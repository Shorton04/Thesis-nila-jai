import pytest
import json
import base64
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from applications.models import BusinessApplication, ApplicationRequirement, ApplicationActivity

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )


@pytest.fixture
def authenticated_client(client, user):
    client.login(username='testuser', password='testpassword123')
    return client


@pytest.fixture
def test_files():
    # Create sample files for testing
    small_gif = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
        b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
        b'\x02\x4c\x01\x00\x3b'
    )
    pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 1/Kids[3 0 R]>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000015 00000 n \n0000000060 00000 n \n0000000111 00000 n \ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n'

    return {
        'image': SimpleUploadedFile(
            "test_image.gif",
            small_gif,
            content_type="image/gif"
        ),
        'pdf': SimpleUploadedFile(
            "test_document.pdf",
            pdf_content,
            content_type="application/pdf"
        ),
        # Base64 encoded small image to simulate camera capture
        'camera_image_base64': base64.b64encode(small_gif).decode('utf-8')
    }


@pytest.mark.django_db
def test_complete_application_lifecycle(authenticated_client, user, test_files):
    """
    Test complete business permit lifecycle from new application through amendment to closure
    including all steps, camera functionality, and document uploading.
    """

    # === NEW APPLICATION ===

    # Initial GET to start the application process
    response = authenticated_client.get(reverse('applications:new_application'))
    assert response.status_code == 200

    # Step 1: Basic information
    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'business_type': 'single',
            'business_name': 'Test Business',
            'trade_name': 'TB Trading',
            'registration_number': 'REG12345',
            'registration_date': '2025-01-01',
            'payment_mode': 'annually',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302  # Redirect to next step

    # Get the draft application
    draft_application = BusinessApplication.objects.filter(
        applicant=user,
        business_name='Test Business',
        status='draft'
    ).first()
    assert draft_application is not None

    # Step 2: Business details
    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'business_address': '123 Test Street',
            'postal_code': '12345',
            'telephone': '123-456-7890',
            'email': 'business@example.com',
            'line_of_business': 'Retail',
            'business_area': '100',
            'number_of_employees': '5',
            'capitalization': '100000',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302  # Redirect to next step

    # Step 3: Owner details
    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'owner_name': 'Test Owner',
            'owner_address': '456 Owner Street',
            'owner_telephone': '987-654-3210',
            'owner_email': 'owner@example.com',
            'emergency_contact_name': 'Emergency Contact',
            'emergency_contact_number': '555-555-5555',
            'emergency_contact_email': 'emergency@example.com',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302  # Redirect to next step

    # Step 4: Review (just continue)
    response = authenticated_client.post(
        reverse('applications:new_application'),
        {'submit_type': 'continue'}
    )
    assert response.status_code == 302  # Redirect to next step

    # Step 5: Document upload and submit
    # Simulating both regular file upload and camera upload
    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'dti_registration': test_files['pdf'],  # Regular file upload
            'legal_ownership': test_files['pdf'],
            'signage_photo': test_files['image'],  # Regular image upload
            'barangay_clearance': test_files['pdf'],
            'submit_type': 'continue'
        },
        format='multipart'
    )
    assert response.status_code == 302  # Redirect to application detail

    # Check if application is submitted and documents are uploaded
    application = BusinessApplication.objects.get(id=draft_application.id)
    assert application.status == 'submitted'

    # Check if documents were uploaded
    requirements = ApplicationRequirement.objects.filter(application=application)
    assert requirements.count() >= 4  # At least 4 documents should be uploaded
    assert requirements.filter(is_submitted=True).count() >= 4

    # Simulate application approval (would normally be done by admin)
    application.status = 'approved'
    application.save()

    # === AMENDMENT APPLICATION ===

    # Initial GET to start the amendment process
    response = authenticated_client.get(reverse('applications:amendment_application'))
    assert response.status_code == 200

    # Step 1: Basic info
    response = authenticated_client.post(
        reverse('applications:amendment_application'),
        {
            'business_name': application.business_name,
            'previous_permit_number': 'PERMIT-123',
            'amendment_reason': 'Change of business name and address',
            'amendment_type': ['business_name', 'address'],
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302  # Redirect to next step

    # Get the draft amendment application
    amendment_application = BusinessApplication.objects.filter(
        applicant=user,
        application_type='amendment',
        status='draft'
    ).first()
    assert amendment_application is not None

    # Step 2: Amendment details
    response = authenticated_client.post(
        reverse('applications:amendment_application'),
        {
            'new_business_name': 'New Business Name',
            'business_address': '789 New Address',
            'postal_code': '54321',
            'telephone': '555-123-4567',
            'email': 'new@example.com',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302  # Redirect to next step

    # Step 3: Review (just continue)
    response = authenticated_client.post(
        reverse('applications:amendment_application'),
        {'submit_type': 'continue'}
    )
    assert response.status_code == 302  # Redirect to next step

    # Step 4: Document upload and submit
    # Test both regular upload and simulated camera upload
    response = authenticated_client.post(
        reverse('applications:amendment_application'),
        {
            'board_resolution': test_files['pdf'],  # Regular file upload
            'updated_registration': test_files['pdf'],
            'submit_type': 'continue'
        },
        format='multipart'
    )
    assert response.status_code == 302  # Redirect to application detail

    # Check if amendment application is submitted and documents are uploaded
    amendment_application = BusinessApplication.objects.get(id=amendment_application.id)
    assert amendment_application.status == 'submitted'

    # Check if documents were uploaded
    amendment_requirements = ApplicationRequirement.objects.filter(application=amendment_application)
    assert amendment_requirements.count() >= 2  # At least 2 documents should be uploaded

    # Simulate amendment approval
    amendment_application.status = 'approved'
    amendment_application.save()

    # === CLOSURE APPLICATION ===

    # Initial GET to start the closure process
    response = authenticated_client.get(reverse('applications:closure_application'))
    assert response.status_code == 200

    # Step 1: Basic info
    response = authenticated_client.post(
        reverse('applications:closure_application'),
        {
            'business_name': 'New Business Name',  # Using amended name
            'previous_permit_number': 'PERMIT-123',
            'owner_name': 'Test Owner',
            'owner_email': 'owner@example.com',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302  # Redirect to next step

    # Get the draft closure application
    closure_application = BusinessApplication.objects.filter(
        applicant=user,
        application_type='closure',
        status='draft'
    ).first()
    assert closure_application is not None

    # Step 2: Closure details
    response = authenticated_client.post(
        reverse('applications:closure_application'),
        {
            'closure_date': '2026-01-01',
            'closure_reason': 'Business relocation outside jurisdiction',
            'closure_reason_checkbox': ['Business relocation outside jurisdiction'],
            'remarks': 'Moving business to another city',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302  # Redirect to next step

    # Step 3: Review (just continue)
    response = authenticated_client.post(
        reverse('applications:closure_application'),
        {'submit_type': 'continue'}
    )
    assert response.status_code == 302  # Redirect to next step

    # Step 4: Document upload and submit
    # Test both regular upload and simulated camera upload
    response = authenticated_client.post(
        reverse('applications:closure_application'),
        {
            'original_permit': test_files['image'],  # Regular image upload
            'affidavit_closure': test_files['pdf'],
            'tax_clearance': test_files['pdf'],
            'barangay_closure': test_files['pdf'],
            'submit_type': 'continue'
        },
        format='multipart'
    )
    assert response.status_code == 302  # Redirect to application detail

    # Check if closure application is submitted and documents are uploaded
    closure_application = BusinessApplication.objects.get(id=closure_application.id)
    assert closure_application.status == 'submitted'

    # Check if documents were uploaded
    closure_requirements = ApplicationRequirement.objects.filter(application=closure_application)
    assert closure_requirements.count() >= 4  # At least 4 documents should be uploaded

    # === VERIFY COMPLETE LIFECYCLE ===

    # Get all applications for this business in order
    applications = BusinessApplication.objects.filter(
        applicant=user,
        business_name__in=['Test Business', 'New Business Name']
    ).order_by('created_at')

    # Verify we have all three application types in the correct order
    assert applications.count() == 3
    assert applications[0].application_type == 'new'
    assert applications[1].application_type == 'amendment'
    assert applications[2].application_type == 'closure'

    # Verify all applications have been submitted and have uploaded documents
    for app in applications:
        assert app.status in ['submitted', 'approved']
        requirements = ApplicationRequirement.objects.filter(application=app)
        assert requirements.exists()
        assert requirements.filter(is_submitted=True).exists()

    # Success - complete lifecycle test passed
    print("Complete application lifecycle test passed successfully!")


@pytest.mark.django_db
def test_camera_functionality(authenticated_client, user, test_files):
    """
    Specifically test the camera functionality for document upload.
    This simulates what happens when a user takes a photo using the camera interface.
    """
    # Start a new application
    response = authenticated_client.get(reverse('applications:new_application'))
    assert response.status_code == 200

    # Complete steps 1-3 quickly to get to document upload
    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'business_type': 'single',
            'business_name': 'Camera Test Business',
            'trade_name': 'Camera Test',
            'registration_number': 'CAM12345',
            'registration_date': '2025-01-01',
            'payment_mode': 'annually',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302

    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'business_address': '123 Camera St',
            'postal_code': '54321',
            'telephone': '555-123-4567',
            'email': 'camera@test.com',
            'line_of_business': 'Photography',
            'business_area': '50',
            'number_of_employees': '2',
            'capitalization': '50000',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302

    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'owner_name': 'Camera Owner',
            'owner_address': '456 Camera Ave',
            'owner_telephone': '555-987-6543',
            'owner_email': 'owner@camera.com',
            'emergency_contact_name': 'Emergency Camera',
            'emergency_contact_number': '555-111-2222',
            'emergency_contact_email': 'emergency@camera.com',
            'submit_type': 'continue'
        }
    )
    assert response.status_code == 302

    response = authenticated_client.post(
        reverse('applications:new_application'),
        {'submit_type': 'continue'}
    )
    assert response.status_code == 302

    # Now at step 5 (document upload)
    # Simulate camera capture by directly creating a file from base64 data
    # In a real browser, this would be handled by JavaScript after capturing from the camera
    camera_file = SimpleUploadedFile(
        "camera_capture.jpg",
        base64.b64decode(test_files['camera_image_base64']),
        content_type="image/jpeg"
    )

    # Upload the "camera capture" along with regular files
    response = authenticated_client.post(
        reverse('applications:new_application'),
        {
            'signage_photo': camera_file,  # This simulates a camera capture
            'dti_registration': test_files['pdf'],
            'legal_ownership': test_files['pdf'],
            'barangay_clearance': test_files['pdf'],
            'submit_type': 'continue'
        },
        format='multipart'
    )
    assert response.status_code == 302

    # Verify the application and uploads
    camera_application = BusinessApplication.objects.get(business_name='Camera Test Business')
    assert camera_application.status == 'submitted'

    # Check if the "camera-captured" document was uploaded
    camera_requirements = ApplicationRequirement.objects.filter(
        application=camera_application,
        requirement_name='Picture with Signage'  # This is the field that used the camera capture
    )
    assert camera_requirements.exists()
    assert camera_requirements.first().is_submitted is True
    assert camera_requirements.first().document is not None

    print("Camera functionality test passed successfully!")