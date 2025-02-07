# reviewer/urls.py
from django.urls import path
from . import views

app_name = 'reviewer'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('applications/', views.application_list, name='application_list'),
    path('applications/<uuid:application_id>/',
         views.application_detail, name='application_detail'),
    path('verify-requirement/<int:requirement_id>/',
         views.verify_requirement, name='verify_requirement'),
    path('create-assessment/<uuid:application_id>/',
         views.create_assessment, name='create_assessment'),
]