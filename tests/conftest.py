# tests/conftest.py
import pytest
from pytest_django.lazy_django import skip_if_no_django

@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath

@pytest.fixture
def client_with_user(client, django_user_model):
    from .factories.user import UserFactory
    user = UserFactory()
    client.force_login(user)
    return client, user