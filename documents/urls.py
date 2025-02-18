# documents/urls.py
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('upload/<uuid:application_id>/', views.upload_document, name='upload_document'),
    path('view/<uuid:document_id>/', views.view_document, name='view_document'),
    path('delete/<uuid:document_id>/', views.delete_document, name='delete_document'),
    path('verification-status/<uuid:document_id>/', views.document_verification_status, name='verification_status'),
]