# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),

    # Email Verification
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # Profile Management
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/security/', views.account_security, name='security'),

    # Password Management
    path('password/change/', views.change_password, name='change_password'),
    path('password/reset/', views.password_reset_request, name='password_reset_request'),
    path('password/reset/confirm/<uuid:token>/',
         views.password_reset_confirm, name='password_reset_confirm'),
]
