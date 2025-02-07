# reviewer/models.py
from django.db import models
from django.conf import settings
from applications.models import BusinessApplication


class ReviewerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=50, unique=True)
    contact_number = models.CharField(max_length=20)
    signature = models.ImageField(upload_to='reviewer_signatures/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"


class ReviewAssignment(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('reassigned', 'Reassigned')
    ]

    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='assignments_given')
    assigned_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    notes = models.TextField(blank=True)
    due_date = models.DateTimeField()
    completed_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.application.application_number} - {self.reviewer.get_full_name()}"