# notifications/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    notification_type = models.CharField(max_length=50, default='info', choices=(
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('application', 'Application'),
        ('document', 'Document'),
        ('system', 'System'),
    ))

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def mark_as_read(self):
        self.is_read = True
        self.save()