# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProfile, LoginHistory, PasswordReset


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
    'email', 'username', 'first_name', 'last_name', 'is_staff', 'is_email_verified', 'company_name', 'business_type')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_email_verified', 'business_type')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Business info'), {'fields': ('company_name', 'position', 'business_type')}),
        (_('Verification'), {'fields': ('is_email_verified', 'verification_token', 'verification_token_created')}),
        (_('Security'), {'fields': ('last_login_ip', 'login_attempts', 'account_locked_until')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'username', 'first_name', 'last_name', 'company_name')
    ordering = ('email',)
    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_datetime', 'ip_address', 'is_successful', 'failure_reason')
    list_filter = ('is_successful', 'login_datetime')
    search_fields = ('user__email', 'ip_address', 'user_agent')
    date_hierarchy = 'login_datetime'


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'used')
    list_filter = ('used', 'created_at')
    search_fields = ('user__email',)
    date_hierarchy = 'created_at'
    readonly_fields = ('token',)


admin.site.register(CustomUser, CustomUserAdmin)