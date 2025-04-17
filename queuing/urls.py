# queuing/urls.py
from django.urls import path
from . import views

app_name = 'queuing'

urlpatterns = [
    # User views
    path('dashboard/', views.queue_dashboard, name='dashboard'),
    path('book/<uuid:application_id>/<str:appointment_type>/', views.book_appointment, name='book_appointment'),
    path('appointment/<uuid:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointment/<uuid:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointment/<uuid:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('appointment/<uuid:appointment_id>/check-in/', views.check_in, name='check_in'),

    # Staff views
    path('staff/dashboard/', views.staff_queue_dashboard, name='staff_dashboard'),
    path('staff/counter/<int:counter_id>/next/', views.call_next, name='call_next'),
    path('staff/update-stats/', views.update_queue_stats, name='update_stats'),
    path('staff/qr-scanner/', views.qr_scanner, name='qr_scanner'),
    path('api/appointments/<uuid:appointment_id>/', views.get_appointment_details, name='get_appointment_details'),
    path('staff/check-in-by-queue/', views.check_in_by_queue, name='check_in_by_queue'),
    path('appointment/<uuid:appointment_id>/status/', views.appointment_status, name='appointment_status'),
    path('staff/api/queue/', views.get_queue, name='get_queue'),
    path('staff/api/mark-no-shows/', views.mark_no_shows, name='mark_no_shows'),

    # Public display
    path('display/', views.queue_display, name='queue_display'),
    path('display/data/', views.queue_display_data, name='queue_display_data'),

    # Staff queue management
    path('staff/queue-management/', views.queue_management, name='queue_management'),
    path('staff/api/counters/', views.get_counters, name='get_counters'),
    path('staff/api/waiting-queue/', views.get_waiting_queue, name='get_waiting_queue'),
    path('staff/api/appointment-details/', views.get_appointment_details, name='get_appointment_details'),
    path('staff/api/available-counters/', views.get_available_counters, name='get_available_counters'),
    path('staff/api/complete-appointment/', views.complete_appointment, name='complete_appointment'),
    path('staff/api/return-to-queue/', views.return_to_queue, name='return_to_queue'),
    path('staff/api/call-specific/', views.call_specific, name='call_specific'),
]