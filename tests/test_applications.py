# tests/test_applications.py
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from applications.models import (
    BusinessApplication,
    ApplicationRequirement,
    ApplicationActivity
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def application(db, user):
    return BusinessApplication.objects.create(
        applicant=user,
        application_type='new',
        payment_mode='annually',
        business_type='single',
        business_name='Test Business',
        registration_number='TEST123',
        registration_date=timezone.now().date(),
        business_address='Test Address',
        postal_code='12345',
        telephone='123-456-7890',
        email='business@example.com',
        line_of_business='Retail',
        business_area=100.0,
        number_of_employees=5,
        capitalization=100000.0,
        owner_name='Test Owner',
        owner_address='Owner Address',
        owner_telephone='098-765-4321',
        owner_email='owner@example.com'
    )


@pytest.mark.django_db
class TestApplicationViews:
    def test_new_application_view_post(self, client, user):
        """Test submitting new application."""
        client.force_login(user)
        url = reverse('applications:new_application')

        data = {
            'business_type': 'single',
            'payment_mode': 'annually',
            'business_name': 'Test Business',
            'trade_name': 'Test Trade',
            'registration_number': 'TEST123',
            'registration_date': timezone.now().date().strftime('%Y-%m-%d'),
            'business_address': 'Test Address',
            'postal_code': '12345',
            'telephone': '123-456-7890',
            'mobile': '0999999999',
            'email': 'test@example.com',
            'line_of_business': 'Retail',
            'business_area': '100.0',
            'number_of_employees': '5',
            'capitalization': '100000.0',
            'owner_name': 'Test Owner',
            'owner_address': 'Owner Address',
            'owner_telephone': '098-765-4321',
            'owner_email': 'owner@example.com',
            'emergency_contact_name': 'Emergency Contact',
            'emergency_contact_number': '12345678',
            'emergency_contact_email': 'emergency@example.com',
            'save_draft': 'Save Draft'  # Important: Add the save_draft action
        }

        response = client.post(url, data)

        # Verify application was created
        application = BusinessApplication.objects.filter(business_name='Test Business').first()
        assert application is not None
        assert application.business_name == 'Test Business'
        assert application.status == 'draft'

    def test_edit_application_view_post(self, client, user, application):
        """Test submitting edited application."""
        client.force_login(user)
        url = reverse('applications:edit_application', args=[application.id])

        data = {
            'business_type': application.business_type,
            'payment_mode': application.payment_mode,
            'business_name': 'Updated Business Name',  # Changed name
            'trade_name': application.trade_name,
            'registration_number': application.registration_number,
            'registration_date': application.registration_date.strftime('%Y-%m-%d'),
            'business_address': application.business_address,
            'postal_code': application.postal_code,
            'telephone': application.telephone,
            'mobile': application.mobile,
            'email': application.email,
            'line_of_business': application.line_of_business,
            'business_area': str(application.business_area),
            'number_of_employees': str(application.number_of_employees),
            'capitalization': str(application.capitalization),
            'owner_name': application.owner_name,
            'owner_address': application.owner_address,
            'owner_telephone': application.owner_telephone,
            'owner_email': application.owner_email,
            'emergency_contact_name': application.emergency_contact_name,
            'emergency_contact_number': application.emergency_contact_number,
            'emergency_contact_email': application.emergency_contact_email,
            'save_draft': 'Save Draft'  # Important: Add the save_draft action
        }

        response = client.post(url, data)

        # Refresh the application from database
        application.refresh_from_db()

        # Verify changes
        assert application.business_name == 'Updated Business Name'
        assert response.status_code == 302  # Should redirect after successful save

    def test_application_redirect_after_save(self, client, user, application):
        """Test saving application with draft status."""
        client.force_login(user)
        url = reverse('applications:edit_application', args=[application.id])

        data = {
            'business_type': application.business_type,
            'payment_mode': application.payment_mode,
            'business_name': 'Updated Business Name',  # Changed name
            'trade_name': application.trade_name,
            'registration_number': application.registration_number,
            'registration_date': application.registration_date.strftime('%Y-%m-%d'),
            'business_address': application.business_address,
            'postal_code': application.postal_code,
            'telephone': application.telephone,
            'mobile': application.mobile,
            'email': application.email,
            'line_of_business': application.line_of_business,
            'business_area': str(application.business_area),
            'number_of_employees': str(application.number_of_employees),
            'capitalization': str(application.capitalization),
            'owner_name': application.owner_name,
            'owner_address': application.owner_address,
            'owner_telephone': application.owner_telephone,
            'owner_email': application.owner_email,
            'emergency_contact_name': application.emergency_contact_name,
            'emergency_contact_number': application.emergency_contact_number,
            'emergency_contact_email': application.emergency_contact_email,
            'save_draft': 'Save Draft'
        }

        response = client.post(url, data, follow=True)

        # Verify application was updated
        application.refresh_from_db()
        assert application.business_name == 'Updated Business Name'
        assert application.status == 'draft'

    @pytest.fixture
    def application(self, user):
        """Fixture for creating a test application."""
        return BusinessApplication.objects.create(
            applicant=user,
            application_type='new',
            payment_mode='annually',
            business_type='single',
            business_name='Test Business',
            trade_name='Test Trade',
            registration_number='TEST123',
            registration_date=timezone.now().date(),
            business_address='Test Address',
            postal_code='12345',
            telephone='123-456-7890',
            mobile='0999999999',
            email='test@example.com',
            line_of_business='Retail',
            business_area=100.0,
            number_of_employees=5,
            capitalization=100000.0,
            owner_name='Test Owner',
            owner_address='Owner Address',
            owner_telephone='098-765-4321',
            owner_email='owner@example.com',
            emergency_contact_name='Emergency Contact',
            emergency_contact_number='12345678',
            emergency_contact_email='emergency@example.com',
            status='draft'
        )