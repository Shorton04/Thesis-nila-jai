# notifications/urls.py
from django.urls import path, re_path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    # Accept both UUID and integer IDs
    re_path(r'^(?P<notification_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\d+)/$', views.notification_detail, name='detail'),
    re_path(r'^(?P<notification_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\d+)/mark-read/$', views.mark_as_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    re_path(r'^(?P<notification_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\d+)/delete/$', views.delete_notification, name='delete'),
    path('api/count/', views.get_notification_count, name='api_count'),
    path('api/recent/', views.get_recent_notifications, name='api_recent'),
    path('test-email/<uuid:application_id>/', views.test_application_email, name='test_application_email'),
]