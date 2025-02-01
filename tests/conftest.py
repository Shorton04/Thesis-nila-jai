# tests/conftest.py
import pytest
from pytest_django.lazy_django import skip_if_no_django
from django.conf import settings
import os
import shutil


@pytest.fixture
def client_with_user(client, django_user_model):
    from .factories.user import UserFactory
    user = UserFactory()
    client.force_login(user)
    return client, user

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Configure test database."""
    with django_db_blocker.unblock():
        pass

@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    """Configure temporary media storage for tests."""
    settings.MEDIA_ROOT = tmpdir.strpath
    yield
    shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

@pytest.fixture
def test_password():
    return 'test-pass123'

@pytest.fixture
def create_user(db, django_user_model, test_password):
    def make_user(**kwargs):
        kwargs['password'] = test_password
        if 'username' not in kwargs:
            kwargs['username'] = 'testuser'
        return django_user_model.objects.create_user(**kwargs)
    return make_user

@pytest.fixture
def auto_login_user(db, client, create_user, test_password):
    def make_auto_login(user=None):
        if user is None:
            user = create_user()
        client.login(username=user.username, password=test_password)
        return client, user
    return make_auto_login