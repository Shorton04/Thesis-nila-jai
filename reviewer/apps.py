# reviewer/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_reviewer_group(sender, **kwargs):
    from django.contrib.auth.models import Group
    Group.objects.get_or_create(name='Reviewers')

class ReviewerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reviewer'

    def ready(self):
        post_migrate.connect(create_reviewer_group, sender=self)