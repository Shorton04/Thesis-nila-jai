# tests/test_applications.py
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from applications.models import (
    BusinessApplication,
    ApplicationRequirement,
    ApplicationActivity,
    ApplicationAssessment,
    ApplicationRevision
)
from applications.forms import (
    BusinessApplicationForm,
    RenewalApplicationForm,
    AmendmentApplicationForm,
    ClosureApplicationForm
)

User = get_user_model()


# Fixtures
@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def application(db, user):
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
        mobile='099999999',
        email='business@test.com',
        line_of_business='Retail',
        business_area=100.0,
        number_of_employees=5,
        capitalization=100000.0,
        owner_name='Test Owner',
        owner_address='Owner Address',
        owner_telephone='098-765-4321',
        owner_email='owner@test.com',
        emergency_contact_name='Emergency Contact',
        emergency_contact_number='12345678',
        emergency_contact_email='emergency@test.com',
        status='draft'
    )


@pytest.fixture
def renewal_application(db, user, application):
    return BusinessApplication.objects.create(
        applicant=user,
        application_type='renewal',
        payment_mode='annually',
        business_type='single',
        business_name='Renewal Business',
        registration_number='RENEWAL123',
        registration_date=timezone.now().date(),
        business_address='Renewal Address',
        postal_code='54321',
        telephone='123-456-7890',
        email='renewal@test.com',
        line_of_business='Retail',
        business_area=200.0,
        number_of_employees=10,
        capitalization=200000.0,
        gross_sales_receipts=500000.0,
        status='draft'
    )


@pytest.fixture
def requirement(db, application):
    return ApplicationRequirement.objects.create(
        application=application,
        requirement_name='Test Requirement',
        is_required=True
    )


@pytest.fixture
def test_file():
    return SimpleUploadedFile(
        "test_doc.pdf",
        b"test file content",
        content_type="application/pdf"
    )


# Model Tests
@pytest.mark.django_db
class TestBusinessApplicationModel:
    def test_create_application(self, user):
        """Test creating a business application."""
        application = BusinessApplication.objects.create(
            applicant=user,
            application_type='new',
            business_name='Test Business',
            registration_number='TEST123',
            registration_date=timezone.now().date(),
        )
        assert application.pk is not None
        assert application.application_number is not None
        assert application.tracking_number is not None
        assert application.status == 'draft'

    def test_application_number_generation(self, application):
        """Test automatic generation of application number."""
        assert application.application_number.startswith('BP-')
        assert str(timezone.now().year) in application.application_number

    def test_tracking_number_generation(self, application):
        """Test automatic generation of tracking number."""
        assert application.tracking_number.startswith('TRK-')
        assert len(application.tracking_number) >= 12

    def test_string_representation(self, application):
        """Test string representation of application."""
        expected = f"{application.business_name} - {application.application_number}"
        assert str(application) == expected


# Form Tests
@pytest.mark.django_db
class TestBusinessApplicationForms:
    def test_business_application_form_valid(self):
        """Test business application form with valid data."""
        data = {
            'business_type': 'single',
            'business_name': 'Test Business',
            'registration_number': 'TEST123',
            'registration_date': timezone.now().date(),
            'business_address': 'Test Address',
            'postal_code': '12345',
            'telephone': '123-456-7890',
            'email': 'test@example.com',
            'payment_mode': 'annually'
        }
        form = BusinessApplicationForm(data=data)
        assert form.is_valid()

    def test_renewal_application_form_valid(self):
        """Test renewal application form with valid data."""
        data = {
            'previous_permit_number': 'OLD123',
            'previous_permit_expiry': timezone.now().date(),
            'business_type': 'single',
            'business_name': 'Test Business',
            'registration_number': 'TEST123',
            'gross_sales_receipts': 500000.00,
            'payment_mode': 'annually'
        }
        form = RenewalApplicationForm(data=data)
        assert form.is_valid()

    def test_amendment_application_form_valid(self):
        """Test amendment application form with valid data."""
        data = {
            'current_permit_number': 'CURR123',
            'amendment_reason': 'Change of address',
            'business_type': 'single',
            'business_name': 'Test Business',
            'business_address': 'New Address'
        }
        form = AmendmentApplicationForm(data=data)
        assert form.is_valid()

    def test_closure_application_form_valid(self):
        """Test closure application form with valid data."""
        data = {
            'business_name': 'Test Business',
            'registration_number': 'TEST123',
            'closure_reason': 'Business relocation',
            'closure_date': timezone.now().date() + timezone.timedelta(days=30)
        }
        form = ClosureApplicationForm(data=data)
        assert form.is_valid()


# View Tests
@pytest.mark.django_db
class TestApplicationViews:
    def test_dashboard_view(self, client, user, application):
        """Test dashboard view."""
        client.force_login(user)
        url = reverse('applications:dashboard')
        response = client.get(url)

        assert response.status_code == 200
        assert 'page_obj' in response.context
        assert application in response.context['page_obj']

    def test_new_application_view(self, client, user):
        """Test new application creation."""
        client.force_login(user)
        url = reverse('applications:new_application')
        data = {
            'business_type': 'single',
            'business_name': 'New Business',
            'registration_number': 'NEW123',
            'registration_date': timezone.now().date(),
            'payment_mode': 'annually',
            'submit_type': 'continue'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert BusinessApplication.objects.filter(business_name='New Business').exists()

    def test_renewal_application_view(self, client, user):
        """Test renewal application creation."""
        client.force_login(user)
        url = reverse('applications:renewal_application')
        data = {
            'previous_permit_number': 'OLD123',
            'previous_permit_expiry': timezone.now().date(),
            'business_type': 'single',
            'business_name': 'Renewal Business',
            'registration_number': 'REN123',
            'gross_sales_receipts': '500000.00',
            'payment_mode': 'annually',
            'action': 'submit'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert BusinessApplication.objects.filter(business_name='Renewal Business').exists()

    def test_requirement_upload(self, client, user, application, requirement, test_file):
        """Test requirement document upload."""
        client.force_login(user)
        url = reverse('applications:requirement_upload', args=[application.id, requirement.id])
        data = {
            'document': test_file,
            'remarks': 'Test upload'
        }
        response = client.post(url, data)
        assert response.status_code == 200
        requirement.refresh_from_db()
        assert requirement.is_submitted

    def test_application_detail_view(self, client, user, application):
        """Test application detail view."""
        client.force_login(user)
        url = reverse('applications:application_detail', args=[application.id])
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['application'] == application


# Integration Tests
@pytest.mark.django_db
class TestApplicationWorkflow:
    def test_complete_application_workflow(self, client, user):
        """Test complete application workflow from creation to approval."""
        client.force_login(user)

        # Create application
        create_url = reverse('applications:new_application')
        create_data = {
            'business_type': 'single',
            'business_name': 'Workflow Test Business',
            'registration_number': 'WORKFLOW123',
            'registration_date': timezone.now().date(),
            'payment_mode': 'annually',
            'submit_type': 'continue'
        }
        response = client.post(create_url, create_data)
        assert response.status_code == 302

        application = BusinessApplication.objects.get(business_name='Workflow Test Business')
        assert application.status == 'draft'

        # Submit application
        detail_url = reverse('applications:application_detail', args=[application.id])
        submit_data = {'action': 'submit'}
        response = client.post(detail_url, submit_data)

        application.refresh_from_db()
        assert application.status == 'submitted'
        assert application.submission_date is not None


# Utility Function Tests
@pytest.mark.django_db
class TestApplicationUtils:
    def test_create_default_requirements(self, application):
        """Test creation of default requirements."""
        from applications.views import create_default_requirements
        create_default_requirements(application)
        requirements = ApplicationRequirement.objects.filter(application=application)
        assert requirements.count() > 0
        assert all(req.is_required for req in requirements)

    def test_create_renewal_requirements(self, renewal_application):
        """Test creation of renewal-specific requirements."""
        from applications.views import create_renewal_requirements
        create_renewal_requirements(renewal_application)
        requirements = ApplicationRequirement.objects.filter(application=renewal_application)
        assert requirements.count() > 0
        assert any('Previous Business Permit' in req.requirement_name for req in requirements)