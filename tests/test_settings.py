# tests/test_settings.py
from django.test.runner import DiscoverRunner

class TestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)