# queuing/models.py
from django.db import models
from django.conf import settings
from applications.models import BusinessApplication
import uuid
from datetime import datetime, timedelta


class QueueSlot(models.Model):
    """Model for predefined queue slots at City Hall"""
    date = models.DateField()
    time_slot = models.TimeField()
    max_appointments = models.IntegerField(default=5)  # Number of people that can be served in this slot
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ('date', 'time_slot')
        ordering = ['date', 'time_slot']

    def get_available_count(self):
        """Returns the number of available appointments in this slot"""
        booked = QueueAppointment.objects.filter(slot_date=self.date, slot_time=self.time_slot,
                                                 status='confirmed').count()
        return max(0, self.max_appointments - booked)

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} {self.time_slot.strftime('%H:%M')} ({self.get_available_count()} slots available)"


class QueueAppointment(models.Model):
    """Model for queue appointments"""
    APPOINTMENT_TYPES = (
        ('payment', 'Payment Processing'),
        ('release', 'Permit Release'),
    )

    STATUS_CHOICES = (
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE, related_name='appointments')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES)

    # Queue details
    queue_number = models.CharField(max_length=10, blank=True)
    slot_date = models.DateField()
    slot_time = models.TimeField()

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    checked_in = models.BooleanField(default=False)
    check_in_time = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Estimated processing time in minutes
    estimated_duration = models.PositiveIntegerField(default=15)

    class Meta:
        ordering = ['slot_date', 'slot_time', 'created_at']

    def save(self, *args, **kwargs):
        if not self.queue_number:
            # Generate queue number: P for payment, R for release + date + sequential number
            prefix = 'P' if self.appointment_type == 'payment' else 'R'
            date_str = self.slot_date.strftime('%m%d')

            # Get the count of appointments for this type on this date
            count = QueueAppointment.objects.filter(
                appointment_type=self.appointment_type,
                slot_date=self.slot_date
            ).count() + 1

            self.queue_number = f"{prefix}{date_str}{count:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.queue_number} - {self.application.business_name} ({self.get_appointment_type_display()})"

    @property
    def estimated_wait_time(self):
        """Calculate estimated wait time based on current queue"""
        if self.checked_in:
            return "Now serving"

        # Get all appointments ahead in the queue
        earlier_appointments = QueueAppointment.objects.filter(
            slot_date=self.slot_date,
            slot_time=self.slot_time,
            status='confirmed',
            checked_in=False,
            created_at__lt=self.created_at
        )

        # Calculate total wait time based on estimated duration
        total_wait = sum(apt.estimated_duration for apt in earlier_appointments)
        return timedelta(minutes=total_wait)


class QueueCounter(models.Model):
    """Model for service counters at City Hall"""
    counter_number = models.CharField(max_length=10)
    counter_type = models.CharField(max_length=20, choices=QueueAppointment.APPOINTMENT_TYPES)
    is_active = models.BooleanField(default=True)
    current_queue = models.ForeignKey(QueueAppointment, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='current_counter')

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Counter {self.counter_number} ({self.get_counter_type_display()}) - {status}"


class QueueStats(models.Model):
    """Model to track queue statistics"""
    date = models.DateField(unique=True)
    avg_wait_time_payment = models.PositiveIntegerField(default=0)  # in minutes
    avg_wait_time_release = models.PositiveIntegerField(default=0)  # in minutes
    avg_processing_time_payment = models.PositiveIntegerField(default=0)  # in minutes
    avg_processing_time_release = models.PositiveIntegerField(default=0)  # in minutes
    peak_hours_start = models.TimeField(null=True, blank=True)
    peak_hours_end = models.TimeField(null=True, blank=True)
    total_served = models.PositiveIntegerField(default=0)
    total_no_shows = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Queue Statistics for {self.date.strftime('%Y-%m-%d')}"