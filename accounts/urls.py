# accounts/urls.py
from django.urls import path
from . import views
from . import views, admin_views
from django.conf.urls.static import static
from django.conf import settings

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('terms/', views.terms_and_conditions, name='terms_and_conditions'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),

    # Email Verification
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # Profile Management
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/security/', views.account_security, name='security'),

    # Password Management
    path('password/change/', views.change_password, name='change_password'),
    path('password-reset/confirm/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/<uuid:token>/',
         views.password_reset_confirm, name='password_reset_confirm'),

    # Admin routes
    path('admin/users/', admin_views.user_list, name='admin_user_list'),
    path('admin/users/create/', admin_views.user_create, name='admin_user_create'),
    path('admin/users/<int:user_id>/', admin_views.user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/edit/', admin_views.user_edit, name='admin_user_edit'),
    path('admin/login-history/', admin_views.login_history, name='admin_login_history'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

