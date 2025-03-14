# notifications/admin.py
from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('title', 'message', 'recipient__username', 'recipient__email')
    date_hierarchy = 'created_at'
    raw_id_fields = ('recipient',)
    readonly_fields = ('created_at',)
    list_per_page = 20