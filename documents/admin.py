# documents/admin.py
from django.contrib import admin
from .models import Document, DocumentVerificationResult, DocumentActivity

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'document_type', 'application', 'uploaded_by', 
                   'verification_status', 'uploaded_at')
    list_filter = ('document_type', 'verification_status', 'uploaded_at')
    search_fields = ('filename', 'application__business_name', 
                    'uploaded_by__email')
    readonly_fields = ('id', 'uploaded_at')
    raw_id_fields = ('application', 'uploaded_by', 'verified_by')

@admin.register(DocumentVerificationResult)
class DocumentVerificationResultAdmin(admin.ModelAdmin):
    list_display = ('document', 'verification_id', 'is_authentic', 
                   'fraud_score', 'created_at')
    list_filter = ('is_authentic', 'created_at')
    search_fields = ('document__filename', 'verification_id')
    readonly_fields = ('verification_id', 'created_at', 'updated_at')

@admin.register(DocumentActivity)
class DocumentActivityAdmin(admin.ModelAdmin):
    list_display = ('document', 'activity_type', 'performed_by', 
                   'performed_at')
    list_filter = ('activity_type', 'performed_at')
    search_fields = ('document__filename', 'performed_by__email', 
                    'details')
    readonly_fields = ('performed_at',)