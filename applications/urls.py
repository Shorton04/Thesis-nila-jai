from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

app_name = 'applications'

urlpatterns = [
                  # Dashboard
                  path('', views.dashboard, name='dashboard'),

                  # Application Types
                  path('new/', views.new_application, name='new_application'),
                  path('renewal/', views.renewal_application, name='renewal_application'),
                  path('amendment/', views.amendment_application, name='amendment_application'),
                  path('closure/', views.closure_application, name='closure_application'),

                  # Application Management
                  path('<uuid:application_id>/', views.application_detail, name='application_detail'),
                  path('<uuid:application_id>/edit/', views.edit_application, name='edit_application'),
                  path('<uuid:application_id>/status/', views.status_detail, name='status_detail'),
                  path('<uuid:application_id>/requirements/', views.requirements, name='requirements'),
                  path('<uuid:application_id>/history/', views.application_history, name='history'),
                  path('track-status/', views.track_status, name='track_status'),
                  path('my-applications/', views.track_status_authenticated, name='my_applications'),
                  path('<uuid:application_id>/status-update/', views.status_update, name='status_update'),

                  # Document Management
                  path('<uuid:application_id>/requirement/<int:requirement_id>/upload/',
                       views.requirement_upload, name='requirement_upload'),
                  path('<uuid:application_id>/requirement/<int:requirement_id>/view/',
                       views.view_requirement, name='view_requirement'),
                  path('<uuid:application_id>/requirement/<int:requirement_id>/delete/',
                       views.delete_requirement, name='delete_requirement'),

                  # API Endpoints
                  path('api/<uuid:application_id>/status-update/',
                       views.status_update, name='status_update'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)