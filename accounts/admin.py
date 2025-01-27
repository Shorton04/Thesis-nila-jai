# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProfile, LoginHistory, PasswordReset


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'company_name', 'is_email_verified',
                    'date_joined', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'is_email_verified', 'business_type')
    search_fields = ('email', 'username', 'company_name', 'phone_number')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username', 'phone_number', 'company_name',
                                         'position', 'business_type')}),
        (_('Verification'), {'fields': ('is_email_verified', 'verification_token',
                                        'verification_token_created')}),
        (_('Security'), {'fields': ('login_attempts', 'account_locked_until',
                                    'last_login_ip')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'country', 'created_at', 'updated_at')
    list_filter = ('country', 'city')
    search_fields = ('user__email', 'user__username', 'address', 'city', 'country')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('User Information'), {
            'fields': ('user', 'profile_picture')
        }),
        (_('Address Information'), {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        (_('Additional Information'), {
            'fields': ('date_of_birth',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_datetime', 'ip_address', 'is_successful',
                    'failure_reason')
    list_filter = ('is_successful', 'login_datetime')
    search_fields = ('user__email', 'ip_address', 'user_agent', 'failure_reason')
    readonly_fields = ('login_datetime',)
    ordering = ('-login_datetime',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'used')
    list_filter = ('used', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('token', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False