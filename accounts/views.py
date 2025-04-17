# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserProfileForm,
    PasswordChangeRequestForm, SetPasswordForm, LoginForm
)
from .models import CustomUser, UserProfile, LoginHistory, PasswordReset
import uuid
from django.contrib.auth import update_session_auth_hash


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_active = True
                user.verification_token = uuid.uuid4()
                user.save()

                # Send verification email
                verification_url = f"{request.scheme}://{request.get_host()}/accounts/verify-email/{user.verification_token}/"
                context = {
                    'user': user,
                    'verification_url': verification_url,
                }

                html_message = render_to_string('accounts/email/verification.html', context)
                text_message = render_to_string('accounts/email/verification.txt', context)

                send_mail(
                    'Verify your email address',
                    text_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                messages.success(request, 'Registration successful. Please check your email to verify your account.')
                return redirect('accounts:login')
            except Exception as e:
                print(f"Registration error: {str(e)}")  # For debugging
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, token):
    try:
        user = CustomUser.objects.get(verification_token=token)

        # Check if token is expired (24 hours)
        if timezone.now() > user.verification_token_created + timezone.timedelta(days=1):
            messages.error(request, 'Verification link has expired. Please request a new one.')
            return redirect('accounts:login')

        user.is_active = True
        user.is_email_verified = True
        user.verification_token = None
        user.save()

        messages.success(request, 'Email verified successfully. You can now log in.')
        return redirect('accounts:login')

    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('accounts:login')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data['remember_me']

            try:
                user = CustomUser.objects.get(email=email)

                # Check if account is locked
                if user.is_account_locked():
                    messages.error(request, 'Account is temporarily locked. Please try again later.')
                    return render(request, 'accounts/login.html', {'form': form})

                # Attempt authentication
                authenticated_user = authenticate(request, username=user.username, password=password)
                if authenticated_user is not None:
                    if not authenticated_user.is_email_verified:
                        messages.error(request, 'Please verify your email address before logging in.')
                        return render(request, 'accounts/login.html', {'form': form})

                    # Create login history record first
                    LoginHistory.objects.create(
                        user=authenticated_user,
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        is_successful=True
                    )

                    # Then login the user
                    login(request, authenticated_user)

                    # Reset login attempts
                    authenticated_user.login_attempts = 0
                    authenticated_user.save()

                    if not remember_me:
                        request.session.set_expiry(0)

                    return redirect('applications:dashboard')

                # Authentication failed
                user.login_attempts += 1
                if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                    user.lock_account()
                    messages.error(request, 'Too many failed attempts. Account locked for 30 minutes.')
                else:
                    messages.error(request, 'Invalid email or password.')
                user.save()

                # Record failed login attempt
                LoginHistory.objects.create(
                    user=user,  # Use the found user object
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    is_successful=False,
                    failure_reason='Invalid password'
                )

            except CustomUser.DoesNotExist:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('accounts:login')


@login_required
def profile(request):
    user_profile = UserProfile.get_or_create_profile(request.user)
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'profile': user_profile,
        'login_history': LoginHistory.objects.filter(user=request.user)[:5]
    })


@login_required
def edit_profile(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]

    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                user_form.save()
                profile_form.save()
                messages.success(request, 'Your profile has been updated successfully.')
                return redirect('accounts:profile')
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
        else:
            for form in [user_form, profile_form]:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
    else:
        user_form = CustomUserChangeForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)

    return render(request, 'accounts/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'user': request.user,
        'profile': user_profile
    })

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('accounts:login')
    return render(request, 'accounts/logout_confirmation.html')


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordChangeRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = CustomUser.objects.get(email=email)

            # Create password reset token
            reset_token = PasswordReset.objects.create(
                user=user,
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )

            # Send reset email
            reset_url = f"{request.scheme}://{request.get_host()}/accounts/password-reset/confirm/{reset_token.token}/"
            context = {
                'user': user,
                'reset_url': reset_url,
                'expires_at': reset_token.expires_at
            }

            html_message = render_to_string('accounts/email/password_reset.html', context)
            text_message = render_to_string('accounts/email/password_reset.txt', context)

            send_mail(
                'Password Reset Request',
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )

            messages.success(request, 'Password reset link has been sent to your email.')
            return redirect('accounts:login')
    else:
        form = PasswordChangeRequestForm()

    return render(request, 'accounts/password_reset_request.html', {'form': form})


def password_reset_confirm(request, token):
    try:
        reset_token = PasswordReset.objects.get(token=token)

        if not reset_token.is_valid():
            messages.error(request, 'Password reset link is invalid or has expired.')
            return redirect('accounts:password_reset_request')

        if request.method == 'POST':
            form = SetPasswordForm(request.POST)
            if form.is_valid():
                user = reset_token.user
                user.set_password(form.cleaned_data['password1'])
                user.save()

                # Mark token as used
                reset_token.mark_as_used()

                messages.success(request, 'Password has been reset successfully. You can now log in.')
                return redirect('accounts:login')
        else:
            form = SetPasswordForm()

        return render(request, 'accounts/password_reset_confirm.html', {'form': form})

    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid password reset link.')
        return redirect('accounts:password_reset_request')


@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Validate inputs
        form_errors = {}
        if not current_password:
            form_errors['current_password'] = 'Current password is required'
        if not password1:
            form_errors['password1'] = 'New password is required'
        if not password2:
            form_errors['password2'] = 'Password confirmation is required'
        if password1 != password2:
            form_errors['password2'] = 'New passwords do not match'
        if len(password1) < 8:
            form_errors['password1'] = 'Password must be at least 8 characters long'

        # Check current password
        if not form_errors and not request.user.check_password(current_password):
            form_errors['current_password'] = 'Current password is incorrect'

        if form_errors:
            for field, error in form_errors.items():
                messages.error(request, error)
            return render(request, 'accounts/change_password.html', {
                'form_errors': form_errors,
            })

        try:
            # Change password
            request.user.set_password(password1)
            # Update password change timestamp if you have this field
            if hasattr(request.user, 'password_changed_at'):
                request.user.password_changed_at = timezone.now()
            request.user.save()

            # Update session so user doesn't get logged out
            update_session_auth_hash(request, request.user)

            messages.success(request, 'Your password was successfully updated!')
            return redirect('accounts:profile')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

    # First time viewing or form submission failed
    return render(request, 'accounts/change_password.html', {'active_tab': 'password'})


@login_required
def account_security(request):
    # Get recent login history
    login_history = LoginHistory.objects.filter(user=request.user).order_by('-login_datetime')[:10]

    # Get failed login attempts
    failed_attempts = login_history.filter(is_successful=False).count()

    context = {
        'login_history': login_history,
        'failed_attempts': failed_attempts,
        'is_two_factor_enabled': False,  # For future implementation
        'last_password_change': request.user.password_changed_at if hasattr(request.user,
                                                                            'password_changed_at') else None,
    }

    return render(request, 'accounts/security.html', context)


def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email, is_email_verified=False)

            # Generate new verification token
            user.verification_token = uuid.uuid4()
            user.verification_token_created = timezone.now()
            user.save()

            # Send new verification email
            verification_url = f"{request.scheme}://{request.get_host()}/accounts/verify-email/{user.verification_token}/"
            context = {
                'user': user,
                'verification_url': verification_url,
            }

            html_message = render_to_string('accounts/email/verification.html', context)
            text_message = render_to_string('accounts/email/verification.txt', context)

            send_mail(
                'Verify your email address',
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )

            messages.success(request, 'A new verification email has been sent.')
        except CustomUser.DoesNotExist:
            messages.error(request, 'No unverified user found with this email address.')

    return redirect('accounts:login')

def terms_and_conditions(request):
    """
    Render the Terms and Conditions page
    """
    return render(request, 'accounts/terms_and_conditions.html')

def privacy_policy(request):
    """
    Render the Privacy Policy page
    """
    return render(request, 'accounts/privacy_policy.html')