# reviewer/admin.py
from django.contrib import admin
from .models import ReviewerProfile, ReviewAssignment

@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'position', 'employee_id', 'contact_number')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'employee_id')

@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ('application', 'reviewer', 'status', 'assigned_date', 'due_date')
    list_filter = ('status',)
    search_fields = ('application__application_number', 'reviewer__email')