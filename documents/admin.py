from django.contrib import admin
from .models import Document, VerificationResult


class VerificationResultInline(admin.StackedInline):
    model = VerificationResult
    can_delete = False
    readonly_fields = ('processed_at',)
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'document_type', 'filename', 'user', 'verification_status', 'uploaded_at')
    list_filter = ('document_type', 'verification_status', 'uploaded_at')
    search_fields = ('original_filename', 'filename', 'user__username', 'user__email')
    readonly_fields = ('uploaded_at', 'verification_timestamp')
    inlines = [VerificationResultInline]

    fieldsets = (
        ('Document Information', {
            'fields': ('document_type', 'file', 'original_filename', 'filename', 'uploaded_at')
        }),
        ('Relation', {
            'fields': ('user', 'application')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verification_timestamp', 'verification_details')
        }),
    )


@admin.register(VerificationResult)
class VerificationResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'is_valid', 'confidence_score', 'fraud_probability', 'processed_at')
    list_filter = ('is_valid', 'processed_at')
    search_fields = ('document__original_filename', 'document__user__username')
    readonly_fields = ('processed_at',)