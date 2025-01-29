# tests/factories/user.py
import factory
from django.contrib.auth import get_user_model
from accounts.models import UserProfile

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_email_verified = True
    phone_number = factory.Sequence(lambda n: f'123456789{n}')
    company_name = factory.Sequence(lambda n: f'Company {n}')
    position = 'Manager'
    business_type = 'Testing'

class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    address = factory.Faker('address')
    city = factory.Faker('city')
    state = factory.Faker('state')
    postal_code = factory.Faker('postcode')
    country = factory.Faker('country')