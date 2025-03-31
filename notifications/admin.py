# notifications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient_link', 'notification_type_badge', 'created_at', 'is_read')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = (
    'title', 'message', 'recipient__email', 'recipient__username', 'recipient__first_name', 'recipient__last_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Details', {
            'fields': ('title', 'message', 'link', 'notification_type')
        }),
        ('Recipient Information', {
            'fields': ('recipient',)
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    )

    actions = ['mark_as_read', 'mark_as_unread']

    def notification_type_badge(self, obj):
        """Display a colored badge for the notification type."""
        type_colors = {
            'info': 'info',
            'success': 'success',
            'warning': 'warning',
            'error': 'danger',
            'application': 'primary',
            'document': 'secondary',
            'system': 'dark',
        }
        color = type_colors.get(obj.notification_type, 'secondary')
        return format_html(
            '<span class="badge badge-pill badge-{}">{}</span>',
            color,
            obj.get_notification_type_display()
        )

    notification_type_badge.short_description = 'Type'

    def recipient_link(self, obj):
        """Create a link to the recipient's admin page."""
        if obj.recipient:
            url = reverse("admin:accounts_customuser_change", args=[obj.recipient.id])
            return format_html('<a href="{}">{}</a>', url, obj.recipient.email)
        return '-'

    recipient_link.short_description = 'Recipient'

    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notifications marked as read.")

    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread."""
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notifications marked as unread.")

    mark_as_unread.short_description = "Mark selected notifications as unread"

    def save_model(self, request, obj, form, change):
        """Log changes to notifications."""
        # You could add custom logging here if needed
        super().save_model(request, obj, form, change)