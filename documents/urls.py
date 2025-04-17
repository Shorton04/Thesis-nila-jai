from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Document upload for an application
    path('upload/<int:application_id>/', views.document_upload, name='document_upload'),

    # Document listing (all user documents)
    path('list/', views.document_list, name='document_list'),

    # Document listing for a specific application
    path('list/<int:application_id>/', views.document_list, name='application_documents'),

    # Document detail
    path('detail/<int:document_id>/', views.document_detail, name='document_detail'),

    # Manual verification (admin only)
    path('review/<int:document_id>/', views.manual_verification, name='manual_verification'),

    # Document resubmission
    path('resubmit/<int:document_id>/', views.resubmit_document, name='resubmit_document'),
]