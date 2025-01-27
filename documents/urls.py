# documents/urls.py

from django.urls import path
from . import views

app_name = 'documents'
'''
urlpatterns = [
    # Document upload and management
    path('upload/<int:application_id>/', views.upload_document, name='upload_document'),
    path('batch-upload/<int:application_id>/', views.batch_upload, name='batch_upload'),
    path('list/<int:application_id>/', views.document_list, name='document_list'),
    path('detail/<int:document_id>/', views.document_detail, name='document_detail'),

    # Document updates and versions
    path('update/<int:document_id>/', views.update_document, name='update_document'),
    path('preview/<int:document_id>/', views.document_preview, name='document_preview'),

    # Document analysis
    path('analysis/<int:document_id>/', views.document_analysis, name='document_analysis'),

    # Document download
    path('download/<int:document_id>/', views.document_download, name='document_download'),
    path('download/<int:document_id>/version/<int:version>/', views.document_download, name='document_version_download'),

    # Document Processing
    path('verify/<int:document_id>/', views.verify_document, name='verify_document'),

    path('reprocess/<int:document_id>/', views.reprocess_document, name='reprocess_document'),

    # Version Management
    path('update/<int:document_id>/', views.update_document, name='update_document'),

    path('versions/<int:document_id>/', views.document_versions, name='document_versions'),

    path('download/<int:document_id>/',
         views.document_download,
         name='document_download'),

    path('download/<int:document_id>/version/<int:version>/', views.document_version_download, name='document_version_download'),

    # Document Analysis and Verification
    path('preview/<int:document_id>/', views.document_preview, name='document_preview'),

    path('analysis/<int:document_id>/', views.document_analysis, name='document_analysis'),

    # OCR and Data Extraction
    path('extract-data/<int:document_id>/', views.extract_document_data, name='extract_document_data'),

    path('validate-data/<int:document_id>/', views.validate_document_data, name='validate_document_data'),

    # Admin and Review
    path('review/<int:document_id>/', views.review_document, name='review_document'),

    path('approve/<int:document_id>/', views.approve_document, name='approve_document'),

    path('reject/<int:document_id>/', views.reject_document, name='reject_document'),

    # API Endpoints for AJAX Operations
    path('api/upload-progress/<str:upload_id>/', views.upload_progress, name='upload_progress'),

    path('api/verification-status/<int:document_id>/', views.verification_status, name='verification_status'),
]
'''