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


# Admin/staff views for queue management
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

    context = {
        'payment_queue': payment_queue,
        'release_queue': release_queue,
        'counters': counters,
        'today_date': today
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
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        messages.error(request, "You don't have permission to perform this action")
        return redirect('home')

    # Only allow check-in on the appointment date - Temporarily disabled for testing
    # today = timezone.now().date()
    # if appointment.slot_date != today:
    #     if request.headers.get('x-requested-with') == 'XMLHttpRequest':
    #         return JsonResponse({'success': False, 'error': 'Can only check in on the appointment date'}, status=400)
    #     messages.error(request, "You can only check in on your appointment date")
    #     return redirect('queuing:appointment_detail', appointment_id=appointment.id)

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
    appointment.save()

    # Create notification for the applicant
    create_notification(
        user=appointment.applicant,
        title="Check-in Successful",
        message=f"You have been checked in for your {appointment.get_appointment_type_display()} appointment. Please wait for your queue number ({appointment.queue_number}) to be called.",
        notification_type='info'
    )

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
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)

    try:
        # Handle both JSON and form data
        if 'application/json' in request.headers.get('content-type', ''):
            data = json.loads(request.body)
            queue_number = data.get('queue_number')
        else:
            queue_number = request.POST.get('queue_number')

        if not queue_number:
            return JsonResponse({'success': False, 'error': 'Queue number is required'}, status=400)

        # Find appointment by queue number
        today = timezone.now().date()
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

        # Check in the appointment
        appointment.checked_in = True
        appointment.check_in_time = timezone.now()
        appointment.save()

        # Create notification for the applicant
        create_notification(
            user=appointment.applicant,
            title="Check-in Successful",
            message=f"You have been checked in for your {appointment.get_appointment_type_display()} appointment. Please wait for your queue number ({appointment.queue_number}) to be called.",
            notification_type='info'
        )

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
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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