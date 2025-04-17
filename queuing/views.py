# queuing/views.py
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, F, Q
from datetime import datetime, timedelta
from .models import QueueSlot, QueueAppointment, QueueCounter, QueueStats
from applications.models import BusinessApplication, ApplicationAssessment
from notifications.utils import create_notification
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import traceback
import logging


@login_required
def queue_dashboard(request):
    """View for applicants to see their upcoming appointments"""
    upcoming_appointments = QueueAppointment.objects.filter(
        applicant=request.user,
        status='confirmed',
        slot_date__gte=timezone.now().date()
    ).order_by('slot_date', 'slot_time')

    past_appointments = QueueAppointment.objects.filter(
        applicant=request.user
    ).exclude(
        status='confirmed',
        slot_date__gte=timezone.now().date()
    ).order_by('-slot_date', '-slot_time')[:5]

    # Get pending applications that need payment or permit release
    pending_payment = BusinessApplication.objects.filter(
        applicant=request.user,
        status='approved',
        assessment__is_paid=False
    ).exclude(appointments__appointment_type='payment', appointments__status='confirmed')

    pending_release = BusinessApplication.objects.filter(
        applicant=request.user,
        status='approved',
        assessment__is_paid=True,
        is_released=False
    ).exclude(appointments__appointment_type='release', appointments__status='confirmed')

    context = {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'pending_payment': pending_payment,
        'pending_release': pending_release
    }
    return render(request, 'queuing/dashboard.html', context)


@login_required
def book_appointment(request, application_id, appointment_type):
    """View to book a payment or release appointment"""
    application = get_object_or_404(BusinessApplication, id=application_id, applicant=request.user)

    # Validate appointment type based on application status
    if appointment_type == 'payment':
        # Only check if application is approved
        if not application.status == 'approved':
            messages.error(request, "This application is not ready for payment.")
            return redirect('applications:application_detail', application_id=application.id)
    elif appointment_type == 'release':
        # Only check if application is approved
        if not application.status == 'approved':
            messages.error(request, "This permit is not ready for release.")
            return redirect('applications:application_detail', application_id=application.id)

    # Check for existing appointments
    existing = QueueAppointment.objects.filter(
        application=application,
        appointment_type=appointment_type,
        status='confirmed'
    ).first()

    if existing:
        messages.warning(request,
                         f"You already have a {appointment_type} appointment scheduled on {existing.slot_date} at {existing.slot_time.strftime('%I:%M %p')}")
        return redirect('queuing:appointment_detail', appointment_id=existing.id)

    # Get available dates for the next 7 days
    today = timezone.now().date()
    slot_dates = []

    # Generate dates (exclude weekends)
    for i in range(7):
        check_date = today + timedelta(days=i)
        # Skip weekends
        if check_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            continue
        slot_dates.append(check_date)

    # Manually create time slots
    time_slots = []
    all_available_slots = []

    # Create time slots from 8 AM to 4:30 PM
    for hour in range(8, 17):  # 8 AM to 4 PM
        # Skip lunch hour (12 PM)
        if hour == 12:
            continue

        for minute in [0, 30]:
            # Skip 4:30 PM
            if hour == 16 and minute == 30:
                continue

            # Format for display
            display_hour = hour if hour <= 12 else hour - 12
            am_pm = "AM" if hour < 12 else "PM"

            time_slots.append({
                'value': f"{hour:02d}:{minute:02d}",
                'display': f"{display_hour}:{minute:02d} {am_pm}"
            })

            # Create available slots for each date and time
            for date in slot_dates:
                # For now, assume 5 slots are available for each time
                available_count = 5

                # Add to available slots list
                all_available_slots.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'time': f"{hour:02d}:{minute:02d}",
                    'available': available_count,
                    'datetime_str': f"{date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}"
                })

    if request.method == 'POST':
        selected_date = request.POST.get('date')
        selected_time = request.POST.get('time')

        if not (selected_date and selected_time):
            messages.error(request, "Please select both date and time for your appointment.")
            return redirect('queuing:book_appointment', application_id=application.id,
                            appointment_type=appointment_type)

        # Create the appointment
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            selected_time = datetime.strptime(selected_time, '%H:%M').time()

            # Create queue appointment
            appointment = QueueAppointment.objects.create(
                application=application,
                applicant=request.user,
                appointment_type=appointment_type,
                slot_date=selected_date,
                slot_time=selected_time,
                estimated_duration=15,  # Default to 15 minutes
                status='confirmed'
            )

            messages.success(request, "Appointment booked successfully!")
            return redirect('queuing:appointment_detail', appointment_id=appointment.id)

        except Exception as e:
            print(f"Error booking appointment: {str(e)}")
            messages.error(request, f"Error booking appointment: {str(e)}")

    # Get queue statistics for recommendations
    recommendations = [
        "Morning slots (8:00 AM - 10:00 AM) generally have shorter wait times.",
        "Avoid peak hours (11:00 AM - 2:00 PM) if possible.",
        "Mid-week days (Tuesday-Thursday) tend to be less busy."
    ]

    # Debug information
    print(f"Total available slots: {len(all_available_slots)}")
    print(f"Available dates: {[date.strftime('%Y-%m-%d') for date in slot_dates]}")

    context = {
        'application': application,
        'appointment_type': appointment_type,
        'appointment_type_display': dict(QueueAppointment.APPOINTMENT_TYPES)[appointment_type],
        'slot_dates': slot_dates,
        'time_slots': time_slots,
        'available_slots': all_available_slots,
        'recommendations': recommendations
    }

    return render(request, 'queuing/book_appointment.html', context)    


@login_required
def appointment_detail(request, appointment_id):
    """View appointment details and QR code"""
    appointment = get_object_or_404(QueueAppointment, id=appointment_id, applicant=request.user)

    # Get estimated wait time
    wait_time = appointment.estimated_wait_time

    # Calculate people ahead in queue
    people_ahead = QueueAppointment.objects.filter(
        slot_date=appointment.slot_date,
        slot_time=appointment.slot_time,
        status='confirmed',
        checked_in=False,
        created_at__lt=appointment.created_at
    ).count()

    # Get queue statistics
    if appointment.appointment_type == 'payment':
        avg_service_time = QueueStats.objects.values('avg_processing_time_payment').order_by('-date').first()
        avg_time = avg_service_time['avg_processing_time_payment'] if avg_service_time else 15
    else:
        avg_service_time = QueueStats.objects.values('avg_processing_time_release').order_by('-date').first()
        avg_time = avg_service_time['avg_processing_time_release'] if avg_service_time else 10

    context = {
        'appointment': appointment,
        'wait_time': wait_time,
        'people_ahead': people_ahead,
        'avg_service_time': avg_time
    }
    return render(request, 'queuing/appointment_detail.html', context)


@login_required
def cancel_appointment(request, appointment_id):
    """Cancel a scheduled appointment"""
    appointment = get_object_or_404(QueueAppointment, id=appointment_id, applicant=request.user)

    if request.method == 'POST':
        # Only allow cancellation for confirmed appointments
        if appointment.status == 'confirmed':
            appointment.status = 'cancelled'
            appointment.save()

            # Create notification
            create_notification(
                user=request.user,
                title="Appointment Cancelled",
                message=f"Your {appointment.get_appointment_type_display()} appointment on {appointment.slot_date.strftime('%A, %B %d, %Y')} at {appointment.slot_time.strftime('%I:%M %p')} has been cancelled.",
                notification_type='info'
            )

            messages.success(request, "Appointment cancelled successfully")
        else:
            messages.error(request, "This appointment cannot be cancelled")

    return redirect('queuing:dashboard')


@login_required
def reschedule_appointment(request, appointment_id):
    """Reschedule an existing appointment"""
    appointment = get_object_or_404(QueueAppointment, id=appointment_id, applicant=request.user)

    # Only allow rescheduling for confirmed appointments
    if appointment.status != 'confirmed':
        messages.error(request, "This appointment cannot be rescheduled")
        return redirect('queuing:appointment_detail', appointment_id=appointment.id)

    # First cancel the current appointment
    appointment.status = 'cancelled'
    appointment.save()

    # Then redirect to book a new one
    messages.info(request, "Please select a new appointment time")
    return redirect('queuing:book_appointment', application_id=appointment.application.id,
                    appointment_type=appointment.appointment_type)


@login_required
def staff_queue_dashboard(request):
    """View for staff to manage the queue"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page")
        return redirect('home')

    today = timezone.now().date()

    # Get today's appointments
    payment_queue = QueueAppointment.objects.filter(
        slot_date=today,
        appointment_type='payment',
        status='confirmed'
    ).order_by('slot_time', 'created_at')

    release_queue = QueueAppointment.objects.filter(
        slot_date=today,
        appointment_type='release',
        status='confirmed'
    ).order_by('slot_time', 'created_at')

    # Get active counters
    counters = QueueCounter.objects.filter(is_active=True)

    # Get statistics
    checked_in_count = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True
    ).count()

    now_serving_count = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True,
        current_counter__isnull=False
    ).count()

    completed_count = QueueAppointment.objects.filter(
        slot_date=today,
        status='completed'
    ).count()

    no_show_count = QueueAppointment.objects.filter(
        slot_date=today,
        status='no_show'
    ).count()

    context = {
        'payment_queue': payment_queue,
        'release_queue': release_queue,
        'counters': counters,
        'today_date': today,
        'checked_in_count': checked_in_count,
        'now_serving_count': now_serving_count,
        'completed_count': completed_count,
        'no_show_count': no_show_count
    }
    return render(request, 'queuing/staff/dashboard.html', context)


@login_required
def call_next(request, counter_id):
    """API endpoint to call the next person in the queue"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    counter = get_object_or_404(QueueCounter, id=counter_id)

    # Mark current appointment as completed if there is one
    if counter.current_queue:
        current = counter.current_queue
        current.status = 'completed'
        current.completion_time = timezone.now()
        current.save()

    # Get next appointment from queue
    next_appointment = QueueAppointment.objects.filter(
        slot_date=timezone.now().date(),
        appointment_type=counter.counter_type,
        status='confirmed',
        checked_in=True,
        current_counter__isnull=True
    ).order_by('slot_time', 'check_in_time').first()

    if not next_appointment:
        # Try to find any appointment that hasn't checked in yet
        next_appointment = QueueAppointment.objects.filter(
            slot_date=timezone.now().date(),
            appointment_type=counter.counter_type,
            status='confirmed',
            checked_in=False,
            current_counter__isnull=True
        ).order_by('slot_time', 'created_at').first()

        if not next_appointment:
            counter.current_queue = None
            counter.save()
            return JsonResponse({'message': 'No more appointments in queue'})

    # Assign appointment to counter
    counter.current_queue = next_appointment
    counter.save()

    # Create notification
    create_notification(
        user=next_appointment.applicant,
        title="You're Up Next!",
        message=f"Your {next_appointment.get_appointment_type_display()} application is now being processed at Counter {counter.counter_number}.",
        notification_type='info'
    )

    return JsonResponse({
        'success': True,
        'appointment': {
            'id': str(next_appointment.id),
            'queue_number': next_appointment.queue_number,
            'business_name': next_appointment.application.business_name,
            'checked_in': next_appointment.checked_in
        }
    })


@login_required
def check_in(request, appointment_id):
    """View or API endpoint for applicants to check in"""
    appointment = get_object_or_404(QueueAppointment, id=appointment_id)

    # Validate that it's the correct user or staff
    if not (request.user == appointment.applicant or request.user.is_staff):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        messages.error(request, "You don't have permission to perform this action")
        return redirect('home')

    # Don't allow duplicate check-ins
    if appointment.checked_in:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Already checked in',
                'appointment': {
                    'id': str(appointment.id),
                    'queue_number': appointment.queue_number,
                    'business_name': appointment.application.business_name,
                    'checked_in': True
                }
            })
        messages.info(request, "You're already checked in for this appointment")
        return redirect('queuing:appointment_detail', appointment_id=appointment.id)

    # Check in the appointment
    appointment.checked_in = True
    appointment.check_in_time = timezone.now()
    appointment.save(update_fields=['checked_in', 'check_in_time'])  # Only update these specific fields

    # Create notification for the applicant
    try:
        create_notification(
            user=appointment.applicant,
            title="Check-in Successful",
            message=f"You have been checked in for your {appointment.get_appointment_type_display()} appointment. Please wait for your queue number ({appointment.queue_number}) to be called.",
            notification_type='info'
        )
    except Exception:
        # Continue even if notification fails
        pass

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'appointment': {
                'id': str(appointment.id),
                'queue_number': appointment.queue_number,
                'business_name': appointment.application.business_name,
                'checked_in': True,
                'check_in_time': appointment.check_in_time.strftime('%I:%M %p')
            }
        })

    messages.success(request, "Check-in successful! Please wait for your queue number to be called.")
    return redirect('queuing:appointment_detail', appointment_id=appointment.id)


@login_required
def update_queue_stats(request):
    """Admin function to update queue statistics"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page")
        return redirect('home')

    if request.method == 'POST':
        # Calculate statistics for yesterday
        yesterday = timezone.now().date() - timedelta(days=1)

        # Get completed appointments
        completed = QueueAppointment.objects.filter(
            slot_date=yesterday,
            status='completed'
        )

        payment_appts = completed.filter(appointment_type='payment')
        release_appts = completed.filter(appointment_type='release')

        # Calculate statistics if we have data
        stats = QueueStats(date=yesterday)

        if payment_appts.exists():
            # Calculate average wait time (from check-in to completion)
            avg_wait_payment = payment_appts.exclude(check_in_time=None).annotate(
                wait_time=F('completion_time') - F('check_in_time')
            ).aggregate(avg=Avg('wait_time'))

            if avg_wait_payment and avg_wait_payment['avg']:
                # Convert to minutes
                stats.avg_wait_time_payment = int(avg_wait_payment['avg'].total_seconds() / 60)

            # Calculate average processing time
            stats.avg_processing_time_payment = stats.avg_wait_time_payment

        if release_appts.exists():
            # Calculate average wait time
            avg_wait_release = release_appts.exclude(check_in_time=None).annotate(
                wait_time=F('completion_time') - F('check_in_time')
            ).aggregate(avg=Avg('wait_time'))

            if avg_wait_release and avg_wait_release['avg']:
                # Convert to minutes
                stats.avg_wait_time_release = int(avg_wait_release['avg'].total_seconds() / 60)

            # Calculate average processing time
            stats.avg_processing_time_release = stats.avg_wait_time_release

        # Determine peak hours
        hourly_counts = completed.exclude(check_in_time=None).extra({
            'hour': "EXTRACT(hour FROM check_in_time)"
        }).values('hour').annotate(count=Count('id')).order_by('-count')

        if hourly_counts.exists():
            peak_hour = hourly_counts.first()['hour']
            stats.peak_hours_start = datetime.strptime(f"{int(peak_hour)}:00", "%H:%M").time()
            stats.peak_hours_end = datetime.strptime(f"{int(peak_hour) + 1}:00", "%H:%M").time()

        # Count total served and no-shows
        stats.total_served = completed.count()
        stats.total_no_shows = QueueAppointment.objects.filter(
            slot_date=yesterday,
            status='no_show'
        ).count()

        # Save the stats
        stats.save()

        messages.success(request, f"Queue statistics for {yesterday} have been updated")
        return redirect('queuing:staff_dashboard')

    return render(request, 'queuing/staff/update_stats.html')


@login_required
def qr_scanner(request):
    """View for staff to scan QR codes for check-in"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page")
        return redirect('home')

    return render(request, 'queuing/staff/qr_scanner.html')


@login_required
def get_appointment_details(request, appointment_id):
    """API endpoint to get appointment details"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        appointment = QueueAppointment.objects.get(id=appointment_id)

        # Return appointment details
        return JsonResponse({
            'id': str(appointment.id),
            'queue_number': appointment.queue_number,
            'business_name': appointment.application.business_name,
            'appointment_type': appointment.get_appointment_type_display(),
            'appointment_time': appointment.slot_time.strftime('%I:%M %p'),
            'appointment_date': appointment.slot_date.strftime('%Y-%m-%d'),
            'checked_in': appointment.checked_in,
            'check_in_time': appointment.check_in_time.strftime('%I:%M %p') if appointment.check_in_time else None,
            'status': appointment.status
        })
    except QueueAppointment.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def check_in_by_queue(request):
    """API endpoint to check in an appointment by queue number"""
    try:
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)

        # Handle both JSON and form data
        queue_number = None
        if 'application/json' in request.content_type:
            data = json.loads(request.body)
            queue_number = data.get('queue_number')
        else:
            queue_number = request.POST.get('queue_number')

        if not queue_number:
            return JsonResponse({'success': False, 'error': 'Queue number is required'}, status=400)

        # Find appointment by queue number
        appointment = QueueAppointment.objects.filter(
            queue_number=queue_number,
            status='confirmed'
        ).first()

        if not appointment:
            return JsonResponse({'success': False, 'error': 'Queue number not found'}, status=404)

        # Check if already checked in
        if appointment.checked_in:
            return JsonResponse({
                'success': False,
                'error': 'Already checked in',
                'appointment': {
                    'id': str(appointment.id),
                    'queue_number': appointment.queue_number,
                    'business_name': appointment.application.business_name,
                    'checked_in': True,
                    'check_in_time': appointment.check_in_time.strftime(
                        '%I:%M %p') if appointment.check_in_time else None
                }
            })

        # Check in the appointment - we're not creating a new record, just updating an existing one
        appointment.checked_in = True
        appointment.check_in_time = timezone.now()
        appointment.save(update_fields=['checked_in', 'check_in_time'])  # Only update these specific fields

        # Create notification for the applicant
        try:
            create_notification(
                user=appointment.applicant,
                title="Check-in Successful",
                message=f"You have been checked in for your {appointment.get_appointment_type_display()} appointment. Please wait for your queue number ({appointment.queue_number}) to be called.",
                notification_type='info'
            )
        except Exception as e:
            # Continue even if notification fails
            pass

        return JsonResponse({
            'success': True,
            'appointment': {
                'id': str(appointment.id),
                'queue_number': appointment.queue_number,
                'business_name': appointment.application.business_name,
                'checked_in': True,
                'check_in_time': appointment.check_in_time.strftime('%I:%M %p')
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@login_required
def appointment_status(request, appointment_id):
    """API endpoint to get current appointment status"""
    appointment = get_object_or_404(QueueAppointment, id=appointment_id)

    # Make sure it's the appointment owner or staff
    if not (request.user == appointment.applicant or request.user.is_staff):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    return JsonResponse({
        'id': str(appointment.id),
        'checked_in': appointment.checked_in,
        'check_in_time': appointment.check_in_time.strftime('%I:%M %p') if appointment.check_in_time else None,
        'status': appointment.status
    })


@login_required
def queue_display(request):
    """Public display view for showing current queue status"""
    # Staff permission check is not needed for this view since it's a display

    # Get active counters with current appointments
    active_counters = QueueCounter.objects.filter(
        is_active=True
    ).select_related('current_queue__application')

    # Get next in line appointments (checked in but not yet called)
    today = timezone.now().date()
    next_in_line = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True,
        current_counter__isnull=True
    ).select_related('application').order_by('check_in_time')[:10]  # Show top 10

    context = {
        'active_counters': active_counters,
        'next_in_line': next_in_line,
        'current_date': today
    }

    return render(request, 'queuing/queue_display.html', context)


@login_required
def queue_display_data(request):
    """API endpoint to get current queue data for the display"""
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX request required'}, status=400)

    # Get active counters with current appointments
    active_counters_data = []
    active_counters = QueueCounter.objects.filter(
        is_active=True
    ).select_related('current_queue__application')

    for counter in active_counters:
        counter_data = {
            'counter_number': counter.counter_number,
            'counter_type': counter.counter_type,
            'current_queue': None
        }

        if counter.current_queue:
            # Check if this appointment was called within the last minute (for blinking effect)
            recently_called = False
            if counter.current_queue.check_in_time:
                time_difference = timezone.now() - counter.current_queue.check_in_time
                recently_called = time_difference.total_seconds() < 60

            counter_data['current_queue'] = {
                'id': str(counter.current_queue.id),
                'queue_number': counter.current_queue.queue_number,
                'business_name': counter.current_queue.application.business_name,
                'recently_called': recently_called
            }

        active_counters_data.append(counter_data)

    # Get next in line appointments (checked in but not yet called)
    today = timezone.now().date()
    next_in_line_data = []
    next_in_line = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True,
        current_counter__isnull=True
    ).select_related('application').order_by('check_in_time')[:10]  # Show top 10

    for appointment in next_in_line:
        # Check if this appointment was checked in within the last minute (for highlight effect)
        recently_added = False
        if appointment.check_in_time:
            time_difference = timezone.now() - appointment.check_in_time
            recently_added = time_difference.total_seconds() < 60

        next_in_line_data.append({
            'id': str(appointment.id),
            'queue_number': appointment.queue_number,
            'business_name': appointment.application.business_name,
            'appointment_type': appointment.appointment_type,
            'checked_in': appointment.checked_in,
            'recently_added': recently_added
        })

    # Add any announcements if needed
    announcements = [
        "Please be ready with your documents when your queue number is called.",
        "Ensure you have checked in at the reception desk upon arrival.",
        "Payment counters accept cash, checks, and bank transfers."
    ]

    return JsonResponse({
        'active_counters': active_counters_data,
        'next_in_line': next_in_line_data,
        'announcements': announcements
    })


@login_required
def queue_management(request):
    """Staff view for managing queues and counters"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page")
        return redirect('home')

    today = timezone.now().date()

    # Get active counters
    counters = QueueCounter.objects.filter(
        is_active=True
    ).select_related('current_queue__application')

    # Get waiting queue
    waiting_queue = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True,
        current_counter__isnull=True
    ).select_related('application').order_by('check_in_time')

    # Statistics
    total_appointments = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed'
    ).count()

    checked_in_count = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True
    ).count()

    now_serving_count = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True,
        current_counter__isnull=False
    ).count()

    waiting_count = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True,
        current_counter__isnull=True
    ).count()

    stats = {
        'total_appointments': total_appointments,
        'checked_in_count': checked_in_count,
        'now_serving_count': now_serving_count,
        'waiting_count': waiting_count
    }

    context = {
        'counters': counters,
        'waiting_queue': waiting_queue,
        'stats': stats
    }

    return render(request, 'queuing/staff/queue_management.html', context)


@login_required
def get_counters(request):
    """API endpoint to get current counter data"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX request required'}, status=400)

    counters_data = []
    counters = QueueCounter.objects.all().select_related('current_queue__application')

    for counter in counters:
        counter_data = {
            'id': counter.id,
            'counter_number': counter.counter_number,
            'counter_type': counter.counter_type,
            'is_active': counter.is_active,
            'current_queue': None
        }

        if counter.current_queue:
            counter_data['current_queue'] = {
                'id': str(counter.current_queue.id),
                'queue_number': counter.current_queue.queue_number,
                'business_name': counter.current_queue.application.business_name,
                'check_in_time': counter.current_queue.check_in_time.strftime('%I:%M %p')
            }

        counters_data.append(counter_data)

    return JsonResponse({'counters': counters_data})


@login_required
def get_waiting_queue(request):
    """API endpoint to get waiting queue data"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX request required'}, status=400)

    today = timezone.now().date()
    waiting_queue_data = []

    waiting_queue = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        checked_in=True
    ).select_related('application', 'current_counter').order_by('check_in_time')

    for appointment in waiting_queue:
        appointment_data = {
            'id': str(appointment.id),
            'queue_number': appointment.queue_number,
            'business_name': appointment.application.business_name,
            'application_id': str(appointment.application.id),
            'application_number': appointment.application.application_number,
            'appointment_type': appointment.appointment_type,
            'checked_in': appointment.checked_in,
            'check_in_time': appointment.check_in_time.strftime('%I:%M %p') if appointment.check_in_time else None,
            'current_counter': appointment.current_counter.counter_number if appointment.current_counter else None
        }

        waiting_queue_data.append(appointment_data)

    return JsonResponse({'waiting_queue': waiting_queue_data})


@login_required
def get_appointment_details(request):
    """API endpoint to get details for a specific appointment"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX request required'}, status=400)

    appointment_id = request.GET.get('appointment_id')
    if not appointment_id:
        return JsonResponse({'error': 'Appointment ID is required'}, status=400)

    try:
        appointment = QueueAppointment.objects.select_related('application').get(id=appointment_id)

        # Get assessment amount for payment appointments
        assessment_amount = None
        if appointment.appointment_type == 'payment' and hasattr(appointment.application, 'assessment'):
            assessment_amount = str(appointment.application.assessment.total_amount)

        appointment_data = {
            'id': str(appointment.id),
            'queue_number': appointment.queue_number,
            'business_name': appointment.application.business_name,
            'application_id': str(appointment.application.id),
            'application_number': appointment.application.application_number,
            'appointment_type': appointment.appointment_type,
            'checked_in': appointment.checked_in,
            'check_in_time': appointment.check_in_time.strftime('%I:%M %p') if appointment.check_in_time else None,
            'assessment_amount': assessment_amount
        }

        return JsonResponse({'success': True, 'appointment': appointment_data})
    except QueueAppointment.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_available_counters(request):
    """API endpoint to get available counters for a specific appointment type"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX request required'}, status=400)

    appointment_type = request.GET.get('appointment_type')
    if not appointment_type:
        return JsonResponse({'error': 'Appointment type is required'}, status=400)

    counters = QueueCounter.objects.filter(
        counter_type=appointment_type,
        is_active=True
    ).select_related('current_queue')

    counters_data = []
    for counter in counters:
        counters_data.append({
            'id': counter.id,
            'counter_number': counter.counter_number,
            'current_queue': counter.current_queue.queue_number if counter.current_queue else None
        })

    return JsonResponse({'counters': counters_data})


@login_required
def complete_appointment(request):
    """API endpoint to complete an appointment and mark it as released"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        counter_id = data.get('counter_id')
        appointment_id = data.get('appointment_id')
        notes = data.get('notes')

        if not counter_id or not appointment_id:
            return JsonResponse({'error': 'Counter ID and Appointment ID are required'}, status=400)

        counter = get_object_or_404(QueueCounter, id=counter_id)
        appointment = get_object_or_404(QueueAppointment, id=appointment_id)

        # Ensure this appointment is actually at this counter
        if counter.current_queue != appointment:
            return JsonResponse({'error': 'This appointment is not currently at this counter'}, status=400)

        # Mark appointment as completed
        appointment.status = 'completed'
        appointment.completion_time = timezone.now()
        appointment.save(update_fields=['status', 'completion_time'])

        # Clear the counter
        counter.current_queue = None
        counter.save(update_fields=['current_queue'])

        # Handle appointment type specific actions
        if appointment.appointment_type == 'payment':
            # Record payment details if provided
            payment_amount = data.get('paymentAmount')
            payment_method = data.get('paymentMethod')
            receipt_number = data.get('receiptNumber')

            # Mark application as paid in the assessment model if it exists
            if hasattr(appointment.application, 'assessment'):
                assessment = appointment.application.assessment
                assessment.is_paid = True
                assessment.payment_date = timezone.now().date()
                assessment.payment_method = payment_method
                assessment.receipt_number = receipt_number
                assessment.payment_amount = payment_amount
                assessment.save()

        elif appointment.appointment_type == 'release':
            # Record release details if provided
            permit_number = data.get('permitNumber')
            release_to = data.get('releaseTo')
            id_presented = data.get('idPresented', False)

            # Mark application as released
            application = appointment.application
            application.is_released = True
            application.release_date = timezone.now().date()
            application.released_to = release_to
            application.permit_number = permit_number
            application.id_presented = id_presented
            application.save()

        # Create notification for the applicant
        create_notification(
            user=appointment.applicant,
            title=f"{appointment.get_appointment_type_display()} Completed",
            message=f"Your {appointment.get_appointment_type_display()} has been completed successfully.",
            notification_type='success'
        )

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def return_to_queue(request):
    """API endpoint to return an appointment to the waiting queue"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        counter_id = data.get('counter_id')
        appointment_id = data.get('appointment_id')

        if not counter_id or not appointment_id:
            return JsonResponse({'error': 'Counter ID and Appointment ID are required'}, status=400)

        counter = get_object_or_404(QueueCounter, id=counter_id)
        appointment = get_object_or_404(QueueAppointment, id=appointment_id)

        # Ensure this appointment is actually at this counter
        if counter.current_queue != appointment:
            return JsonResponse({'error': 'This appointment is not currently at this counter'}, status=400)

        # Return appointment to queue
        counter.current_queue = None
        counter.save(update_fields=['current_queue'])

        # Create notification for the applicant
        create_notification(
            user=appointment.applicant,
            title="Returned to Queue",
            message=f"Your {appointment.get_appointment_type_display()} has been returned to the waiting queue. Please wait to be called again.",
            notification_type='info'
        )

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def call_specific(request):
    """API endpoint to call a specific appointment to a counter"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        counter_id = data.get('counter_id')
        appointment_id = data.get('appointment_id')

        if not counter_id or not appointment_id:
            return JsonResponse({'error': 'Counter ID and Appointment ID are required'}, status=400)

        counter = get_object_or_404(QueueCounter, id=counter_id)
        appointment = get_object_or_404(QueueAppointment, id=appointment_id)

        # Check if counter is available
        if counter.current_queue:
            return JsonResponse({'error': 'This counter is already serving another appointment'}, status=400)

        # Check if appointment is already at a counter
        if appointment.current_counter:
            return JsonResponse({'error': 'This appointment is already being served at another counter'}, status=400)

        # Call appointment to counter
        counter.current_queue = appointment
        counter.save(update_fields=['current_queue'])

        # Create notification for the applicant
        create_notification(
            user=appointment.applicant,
            title="You're Up Next!",
            message=f"Your {appointment.get_appointment_type_display()} appointment is now being processed at Counter {counter.counter_number}.",
            notification_type='info'
        )

        return JsonResponse({'success': True, 'counter_number': counter.counter_number})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_queue(request):
    """API endpoint to get queue data for a specific type"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX request required'}, status=400)

    queue_type = request.GET.get('type')
    if queue_type not in ['payment', 'release']:
        return JsonResponse({'error': 'Invalid queue type'}, status=400)

    today = timezone.now().date()
    appointments = QueueAppointment.objects.filter(
        slot_date=today,
        status='confirmed',
        appointment_type=queue_type
    ).select_related('application', 'current_counter').order_by('slot_time')

    counters = QueueCounter.objects.filter(
        counter_type=queue_type,
        is_active=True
    )

    appointments_data = []
    for appointment in appointments:
        appointments_data.append({
            'id': str(appointment.id),
            'queue_number': appointment.queue_number,
            'business_name': appointment.application.business_name,
            'application_id': str(appointment.application.id),
            'slot_time': appointment.slot_time.strftime('%I:%M %p'),
            'checked_in': appointment.checked_in,
            'current_counter': appointment.current_counter.counter_number if appointment.current_counter else None
        })

    counters_data = []
    for counter in counters:
        counters_data.append({
            'id': counter.id,
            'counter_number': counter.counter_number,
            'counter_type': counter.counter_type
        })

    return JsonResponse({
        'appointments': appointments_data,
        'counters': counters_data
    })


@login_required
def mark_no_shows(request):
    """API endpoint to mark appointments as no-shows"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        today = timezone.now().date()
        current_time = timezone.now().time()

        # Find appointments that are scheduled for today, not checked in, and the time has passed
        no_show_appointments = QueueAppointment.objects.filter(
            slot_date=today,
            status='confirmed',
            checked_in=False,
            slot_time__lt=current_time
        )

        count = no_show_appointments.count()

        # Mark them as no_show
        no_show_appointments.update(status='no_show')

        # Get total no-shows count
        total_no_shows = QueueAppointment.objects.filter(
            slot_date=today,
            status='no_show'
        ).count()

        return JsonResponse({
            'success': True,
            'count': count,
            'total_no_shows': total_no_shows
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)