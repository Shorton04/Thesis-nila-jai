# applications/urls.py
from django.urls import path
from . import views
from . import admin_views

app_name = 'applications'

urlpatterns = [
    # Public views
    path('', views.dashboard, name='dashboard'),
    path('new/', views.new_application, name='new_application'),
    path('renewal/', views.renewal_application, name='renewal_application'),
    path('amendment/', views.amendment_application, name='amendment_application'),
    path('closure/', views.closure_application, name='closure_application'),

    # Application management
    path('<uuid:application_id>/', views.application_detail, name='application_detail'),
    path('<uuid:application_id>/edit/', views.edit_application, name='edit_application'),
    path('<uuid:application_id>/submit/', views.submit_application, name='submit_application'),
    path('<uuid:application_id>/cancel/', views.cancel_application, name='cancel_application'),
    path('<uuid:application_id>/history/', views.application_history, name='application_history'),

    # Requirements
    path('<uuid:application_id>/requirement/<int:requirement_id>/upload/',
         views.upload_requirement, name='upload_requirement'),

    # Tracking
    path('track/<str:tracking_number>/', views.track_application, name='track_application'),

    # Admin views
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/reviews/', admin_views.application_review_list, name='admin_review_list'),
    path('admin/review/<uuid:application_id>/',
         admin_views.review_application, name='admin_review_application'),

    # Assessment and payment
    path('admin/<uuid:application_id>/assessment/create/',
         admin_views.create_assessment, name='create_assessment'),
    path('admin/<uuid:application_id>/payment/verify/',
         admin_views.verify_payment, name='verify_payment'),

    # Requirement verification
    path('admin/requirement/<int:requirement_id>/verify/',
         admin_views.requirement_verification, name='requirement_verification'),
]