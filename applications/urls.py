from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('new/', views.new_application, name='new_application'),
    path('renewal/', views.renewal_application, name='renewal_application'),
    path('amendment/', views.amendment_application, name='amendment_application'),
    path('closure/', views.closure_application, name='closure_application'),
    path('<uuid:application_id>/', views.application_detail, name='application_detail'),
    path('<uuid:application_id>/requirement/<int:requirement_id>/upload/',
         views.requirement_upload, name='requirement_upload'),
    path('<uuid:application_id>/requirement/<int:requirement_id>/view/',
         views.view_requirement, name='view_requirement'),
    path('<uuid:application_id>/edit_application/', views.edit_application, name='edit_application'),
    path('<uuid:application_id>/history/', views.application_history, name='application_history'),
]