# queuing/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import QueueSlot, QueueAppointment, QueueCounter, QueueStats


@admin.register(QueueSlot)
class QueueSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'time_slot', 'max_appointments', 'available_slots', 'is_available')
    list_filter = ('date', 'is_available')
    search_fields = ('date', 'time_slot')
    date_hierarchy = 'date'
    ordering = ['date', 'time_slot']

    def available_slots(self, obj):
        available = obj.get_available_count()
        total = obj.max_appointments

        # Color-code based on availability
        if available == 0:
            return format_html('<span style="color: red; font-weight: bold">Full (0/{0})</span>', total)
        elif available < total / 3:  # Less than 1/3 available
            return format_html('<span style="color: orange">{0}/{1}</span>', available, total)
        else:
            return format_html('<span style="color: green">{0}/{1}</span>', available, total)

    available_slots.short_description = 'Available Slots'

    actions = ['mark_as_available', 'mark_as_unavailable']

    def mark_as_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f"{updated} slots marked as available.")

    mark_as_available.short_description = "Mark selected slots as available"

    def mark_as_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f"{updated} slots marked as unavailable.")

    mark_as_unavailable.short_description = "Mark selected slots as unavailable"


@admin.register(QueueAppointment)
class QueueAppointmentAdmin(admin.ModelAdmin):
    list_display = ('queue_number', 'appointment_type_badge', 'business_name', 'slot_date',
                    'slot_time', 'status_badge', 'checked_in', 'waiting_time')
    list_filter = ('appointment_type', 'status', 'checked_in', 'slot_date')
    search_fields = ('queue_number', 'application__business_name', 'applicant__email')
    readonly_fields = ('queue_number', 'created_at', 'updated_at', 'estimated_wait_time')
    date_hierarchy = 'slot_date'

    fieldsets = (
        ('Appointment Information', {
            'fields': ('queue_number', 'appointment_type', 'application', 'applicant')
        }),
        ('Schedule', {
            'fields': ('slot_date', 'slot_time', 'estimated_duration', 'estimated_wait_time')
        }),
        ('Status', {
            'fields': ('status', 'checked_in', 'check_in_time', 'completion_time')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def business_name(self, obj):
        return obj.application.business_name

    business_name.short_description = 'Business Name'

    def waiting_time(self, obj):
        if obj.checked_in:
            return "Now serving"
        elif obj.status != 'confirmed':
            return "-"
        else:
            return obj.estimated_wait_time

    waiting_time.short_description = 'Est. Wait Time'

    def appointment_type_badge(self, obj):
        badge_class = 'primary' if obj.appointment_type == 'payment' else 'success'
        return format_html(
            '<span class="badge badge-pill badge-{}">{}</span>',
            badge_class,
            obj.get_appointment_type_display()
        )

    appointment_type_badge.short_description = 'Type'

    def status_badge(self, obj):
        badge_classes = {
            'confirmed': 'info',
            'completed': 'success',
            'cancelled': 'secondary',
            'no_show': 'danger',
        }
        return format_html(
            '<span class="badge badge-pill badge-{}">{}</span>',
            badge_classes.get(obj.status, 'secondary'),
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    actions = ['mark_as_checked_in', 'mark_as_completed', 'mark_as_no_show', 'mark_as_cancelled']

    def mark_as_checked_in(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status='confirmed', checked_in=False).update(
            checked_in=True,
            check_in_time=now
        )
        self.message_user(request, f"{updated} appointments marked as checked in.")

    mark_as_checked_in.short_description = "Mark selected appointments as checked in"

    def mark_as_completed(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status='confirmed').update(
            status='completed',
            completion_time=now
        )
        self.message_user(request, f"{updated} appointments marked as completed.")

    mark_as_completed.short_description = "Mark selected appointments as completed"

    def mark_as_no_show(self, request, queryset):
        updated = queryset.filter(status='confirmed').update(status='no_show')
        self.message_user(request, f"{updated} appointments marked as no show.")

    mark_as_no_show.short_description = "Mark selected appointments as no show"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.filter(status='confirmed').update(status='cancelled')
        self.message_user(request, f"{updated} appointments marked as cancelled.")

    mark_as_cancelled.short_description = "Mark selected appointments as cancelled"


@admin.register(QueueCounter)
class QueueCounterAdmin(admin.ModelAdmin):
    list_display = ('counter_number', 'counter_type', 'is_active', 'current_queue_display')
    list_filter = ('counter_type', 'is_active')
    search_fields = ('counter_number',)

    def current_queue_display(self, obj):
        if obj.current_queue:
            return format_html(
                '<strong>{0}</strong> - {1}',
                obj.current_queue.queue_number,
                obj.current_queue.application.business_name
            )
        return "No active queue"

    current_queue_display.short_description = "Current Queue"

    actions = ['activate_counters', 'deactivate_counters', 'clear_current_queue']

    def activate_counters(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} counters activated.")

    activate_counters.short_description = "Activate selected counters"

    def deactivate_counters(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} counters deactivated.")

    deactivate_counters.short_description = "Deactivate selected counters"

    def clear_current_queue(self, request, queryset):
        updated = queryset.update(current_queue=None)
        self.message_user(request, f"Current queue cleared for {updated} counters.")

    clear_current_queue.short_description = "Clear current queue for selected counters"


@admin.register(QueueStats)
class QueueStatsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_served', 'total_no_shows', 'payment_wait_time',
                    'release_wait_time', 'peak_period')
    list_filter = ('date',)
    date_hierarchy = 'date'

    readonly_fields = ('date', 'avg_wait_time_payment', 'avg_wait_time_release',
                       'avg_processing_time_payment', 'avg_processing_time_release',
                       'peak_hours_start', 'peak_hours_end', 'total_served', 'total_no_shows')

    def payment_wait_time(self, obj):
        return f"{obj.avg_wait_time_payment} min (process: {obj.avg_processing_time_payment} min)"

    payment_wait_time.short_description = "Payment Wait Time"

    def release_wait_time(self, obj):
        return f"{obj.avg_wait_time_release} min (process: {obj.avg_processing_time_release} min)"

    release_wait_time.short_description = "Release Wait Time"

    def peak_period(self, obj):
        if obj.peak_hours_start and obj.peak_hours_end:
            return f"{obj.peak_hours_start.strftime('%H:%M')} - {obj.peak_hours_end.strftime('%H:%M')}"
        return "Not available"

    peak_period.short_description = "Peak Hours"

    def has_add_permission(self, request):
        # Stats should be automatically generated, not manually added
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of stats
        return False