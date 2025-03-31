# reviewer/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import ReviewerProfile, ReviewAssignment


@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ('reviewer_name', 'department', 'position', 'employee_id', 'contact_number', 'has_signature')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'department', 'position', 'employee_id')
    list_filter = ('department', 'position')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Reviewer Details', {
            'fields': ('department', 'position', 'employee_id', 'contact_number', 'signature')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def reviewer_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    reviewer_name.short_description = 'Name'

    def has_signature(self, obj):
        if obj.signature:
            return format_html('<img src="{}" width="50" height="25" />', obj.signature.url)
        return format_html('<span style="color:red">✘</span>')

    has_signature.short_description = 'Signature'


@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ('application_link', 'reviewer_link', 'status_badge', 'assigned_date',
                    'due_date_display', 'completed_date')
    list_filter = ('status', 'assigned_date', 'due_date')
    search_fields = ('application__application_number', 'application__business_name',
                     'reviewer__first_name', 'reviewer__last_name', 'reviewer__email')
    readonly_fields = ('assigned_date',)
    date_hierarchy = 'assigned_date'

    fieldsets = (
        ('Assignment Information', {
            'fields': ('application', 'reviewer', 'assigned_by')
        }),
        ('Status', {
            'fields': ('status', 'assigned_date', 'due_date', 'completed_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

    def application_link(self, obj):
        url = reverse("admin:applications_businessapplication_change",
                      args=[obj.application.id])
        return format_html('<a href="{}">{} - {}</a>',
                           url,
                           obj.application.application_number,
                           obj.application.business_name)

    application_link.short_description = 'Application'

    def reviewer_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.reviewer.id])
        return format_html('<a href="{}">{}</a>',
                           url,
                           obj.reviewer.get_full_name() or obj.reviewer.email)

    reviewer_link.short_description = 'Reviewer'

    def status_badge(self, obj):
        status_colors = {
            'assigned': 'info',
            'in_progress': 'primary',
            'completed': 'success',
            'reassigned': 'warning',
        }
        return format_html(
            '<span class="badge badge-pill badge-{}">{}</span>',
            status_colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def due_date_display(self, obj):
        now = timezone.now()
        if obj.status in ['completed', 'reassigned']:
            return obj.due_date.strftime('%Y-%m-%d %H:%M')

        if obj.due_date < now:
            return format_html('<span style="color:red;font-weight:bold;">{} (Overdue)</span>',
                               obj.due_date.strftime('%Y-%m-%d %H:%M'))
        elif obj.due_date < (now + timezone.timedelta(days=1)):
            return format_html('<span style="color:orange;font-weight:bold;">{} (Due soon)</span>',
                               obj.due_date.strftime('%Y-%m-%d %H:%M'))
        else:
            return obj.due_date.strftime('%Y-%m-%d %H:%M')

    due_date_display.short_description = 'Due Date'

    actions = ['mark_in_progress', 'mark_completed', 'extend_due_date']

    def mark_in_progress(self, request, queryset):
        updated = queryset.filter(status='assigned').update(status='in_progress')
        self.message_user(request, f"{updated} assignments marked as in progress.")

    mark_in_progress.short_description = "Mark selected assignments as in progress"

    def mark_completed(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status__in=['assigned', 'in_progress']).update(
            status='completed',
            completed_date=now
        )
        self.message_user(request, f"{updated} assignments marked as completed.")

    mark_completed.short_description = "Mark selected assignments as completed"

    def extend_due_date(self, request, queryset):
        # Extend by 24 hours
        extension = timezone.timedelta(days=1)
        for assignment in queryset:
            assignment.due_date = assignment.due_date + extension
            assignment.save()

        self.message_user(request, f"Due date extended by 24 hours for {queryset.count()} assignments.")

    extend_due_date.short_description = "Extend due date by 24 hours"

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.assigned_by = request.user

        if 'status' in form.changed_data and obj.status == 'completed' and not obj.completed_date:
            obj.completed_date = timezone.now()

        super().save_model(request, obj, form, change)