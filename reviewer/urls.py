# reviewer/urls.py
from django.urls import path
from . import views

app_name = 'reviewer'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/counts/', views.dashboard_counts, name='dashboard_counts'),
    path('applications/', views.application_list, name='application_list'),
    path('applications/<uuid:application_id>/',
         views.application_detail, name='application_detail'),
    path('verify-requirement/<int:requirement_id>/',
         views.verify_requirement, name='verify_requirement'),
    path('create-assessment/<uuid:application_id>/',
         views.create_assessment, name='create_assessment'),
    path('document-analysis/<uuid:requirement_id>/', views.document_analysis, name='document_analysis'),
    path('quarantined-documents/', views.quarantined_documents, name='quarantined_documents'),
    path('document-ai-analysis/<uuid:document_id>/', views.document_ai_analysis, name='document_ai_analysis'),
    path('release-document/<uuid:document_id>/', views.release_document, name='release_document'),
    path('qr-scanner/', views.qr_scanner, name='qr_scanner'),
    path('process-qr-code/', views.process_qr_code, name='process_qr_code'),
]