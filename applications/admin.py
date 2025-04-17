# applications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    BusinessApplication,
    ApplicationRequirement,
    ApplicationRevision,
    ApplicationAssessment,
    ApplicationActivity
)


class ApplicationRequirementInline(admin.TabularInline):
    model = ApplicationRequirement
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('requirement_name', 'document', 'is_required', 'is_submitted',
              'is_verified', 'verification_date', 'verified_by', 'remarks')


class ApplicationRevisionInline(admin.StackedInline):
    model = ApplicationRevision
    extra = 0
    readonly_fields = ('revision_number', 'requested_date', 'resolved_date')
    fields = ('revision_number', 'requested_by', 'requested_date', 'deadline',
              'description', 'is_resolved', 'resolved_date', 'resolved_by', 'comments')


class ApplicationAssessmentInline(admin.StackedInline):
    model = ApplicationAssessment
    extra = 0
    readonly_fields = ('assessment_date',)
    fields = ('assessed_by', 'assessment_date', 'total_amount', 'payment_deadline',
              'is_paid', 'payment_date', 'payment_reference', 'remarks')


class ApplicationActivityInline(admin.TabularInline):
    model = ApplicationActivity
    extra = 0
    readonly_fields = ('performed_at', 'performed_by', 'activity_type', 'description')
    fields = ('activity_type', 'performed_by', 'performed_at', 'description')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BusinessApplication)
class BusinessApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_number', 'business_name', 'application_type',
                    'status', 'applicant', 'created_at', 'status_badge')
    list_filter = ('application_type', 'status', 'business_type', 'payment_mode', 'is_released')
    search_fields = ('application_number', 'tracking_number', 'business_name',
                     'trade_name', 'applicant__email', 'applicant__first_name',
                     'applicant__last_name')
    readonly_fields = ('id', 'application_number', 'tracking_number', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Application Information', {
            'fields': ('id', 'application_number', 'tracking_number', 'application_type',
                       'status', 'payment_mode', 'applicant')
        }),
        ('Business Details', {
            'fields': ('business_type', 'business_name', 'trade_name', 'registration_number',
                       'registration_date')
        }),
        ('Contact Information', {
            'fields': ('business_address', 'postal_code', 'telephone', 'mobile',
                       'email', 'website')
        }),
        ('Business Activity', {
            'fields': ('line_of_business', 'business_area', 'number_of_employees',
                       'capitalization')
        }),
        ('Owner Details', {
            'fields': ('owner_name', 'owner_address', 'owner_telephone', 'owner_email')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_number',
                       'emergency_contact_email')
        }),
        ('Financial Information', {
            'fields': ('gross_sales_receipts', 'gross_essential', 'gross_non_essential'),
            'classes': ('collapse',),
        }),
        ('Permit Processing', {
            'fields': ('submission_date', 'is_released', 'release_date', 'released_by',
                       'reviewed_by', 'approved_by', 'remarks')
        }),
        ('Amendment/Closure', {
            'fields': ('previous_permit_number', 'amendment_reason', 'closure_reason',
                       'closure_date'),
            'classes': ('collapse',),
        }),
        ('System', {
            'fields': ('created_at', 'updated_at', 'is_active'),
            'classes': ('collapse',),
        }),
    )

    inlines = [
        ApplicationRequirementInline,
        ApplicationRevisionInline,
        ApplicationAssessmentInline,
        ApplicationActivityInline,
    ]

    def status_badge(self, obj):
        status_colors = {
            'draft': 'secondary',
            'submitted': 'info',
            'under_review': 'primary',
            'requires_revision': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'closed': 'dark',
        }
        color = status_colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-pill badge-{}">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not change:  # If this is a new object
            obj.save()
            # Log creation activity
            ApplicationActivity.objects.create(
                application=obj,
                activity_type='create',
                performed_by=request.user,
                description=f"Application created by {request.user.get_full_name() or request.user.email}"
            )
        else:
            # Check if status changed
            if 'status' in form.changed_data:
                old_status = BusinessApplication.objects.get(pk=obj.pk).status
                new_status = obj.status
                activity_type = 'update'

                # Map status changes to activity types
                if new_status == 'submitted':
                    activity_type = 'submit'
                elif new_status == 'under_review':
                    activity_type = 'review'
                elif new_status == 'requires_revision':
                    activity_type = 'revise'
                elif new_status == 'approved':
                    activity_type = 'approve'
                    obj.approved_by = request.user
                elif new_status == 'rejected':
                    activity_type = 'reject'

                # Log the status change
                ApplicationActivity.objects.create(
                    application=obj,
                    activity_type=activity_type,
                    performed_by=request.user,
                    description=f"Status changed from {old_status} to {new_status} by {request.user.get_full_name() or request.user.email}",
                    meta_data={
                        'old_status': old_status,
                        'new_status': new_status,
                        'changed_fields': form.changed_data
                    }
                )

            # Always log general updates for other fields
            elif form.changed_data:
                ApplicationActivity.objects.create(
                    application=obj,
                    activity_type='update',
                    performed_by=request.user,
                    description=f"Application updated by {request.user.get_full_name() or request.user.email}",
                    meta_data={'changed_fields': form.changed_data}
                )

            obj.save()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            # Set the verified_by for ApplicationRequirement if being verified
            if isinstance(instance, ApplicationRequirement) and instance.is_verified and not instance.verified_by:
                instance.verified_by = request.user

            # Handle comments in ApplicationRevision as ApplicationActivity entries
            if isinstance(instance, ApplicationRevision) and 'comments' in formset.changed_objects:
                ApplicationActivity.objects.create(
                    application=instance.application,
                    activity_type='comment',
                    performed_by=request.user,
                    description=f"Revision comment added by {request.user.get_full_name() or request.user.email}"
                )

            # Handle ApplicationAssessment payment updates
            if isinstance(instance, ApplicationAssessment) and instance.is_paid and not instance.payment_date:
                instance.payment_date = timezone.now()
                ApplicationActivity.objects.create(
                    application=instance.application,
                    activity_type='payment',
                    performed_by=request.user,
                    description=f"Payment recorded by {request.user.get_full_name() or request.user.email}",
                    meta_data={'amount': str(instance.total_amount), 'reference': instance.payment_reference}
                )

            instance.save()

        # Delete objects
        for obj in formset.deleted_objects:
            obj.delete()


@admin.register(ApplicationRequirement)
class ApplicationRequirementAdmin(admin.ModelAdmin):
    list_display = ('requirement_name', 'application', 'is_required', 'is_submitted', 'is_verified')
    list_filter = ('is_required', 'is_submitted', 'is_verified', 'verification_date')
    search_fields = ('requirement_name', 'application__application_number', 'application__business_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ApplicationRevision)
class ApplicationRevisionAdmin(admin.ModelAdmin):
    list_display = ('application', 'revision_number', 'requested_by', 'requested_date', 'is_resolved')
    list_filter = ('is_resolved', 'requested_date', 'deadline')
    search_fields = ('application__application_number', 'application__business_name', 'description')
    readonly_fields = ('revision_number', 'requested_date', 'resolved_date')


@admin.register(ApplicationAssessment)
class ApplicationAssessmentAdmin(admin.ModelAdmin):
    list_display = ('application', 'assessed_by', 'assessment_date', 'total_amount', 'is_paid')
    list_filter = ('is_paid', 'assessment_date', 'payment_date')
    search_fields = ('application__application_number', 'application__business_name', 'payment_reference')
    readonly_fields = ('assessment_date',)


@admin.register(ApplicationActivity)
class ApplicationActivityAdmin(admin.ModelAdmin):
    list_display = ('application', 'activity_type', 'performed_by', 'performed_at')
    list_filter = ('activity_type', 'performed_at')
    search_fields = ('application__application_number', 'application__business_name', 'description')
    readonly_fields = ('performed_at',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False