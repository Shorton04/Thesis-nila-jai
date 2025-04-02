from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import CustomUser
import uuid


@shared_task
def send_verification_email(user_id, verification_url):
    """
    Send verification email asynchronously
    """
    try:
        user = CustomUser.objects.get(id=user_id)
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

        return f"Verification email sent to {user.email}"
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} not found"
    except Exception as e:
        return f"Error sending verification email: {str(e)}"


@shared_task
def send_password_reset_email(user_id, reset_url, expires_at):
    """
    Send password reset email asynchronously
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        context = {
            'user': user,
            'reset_url': reset_url,
            'expires_at': expires_at
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

        return f"Password reset email sent to {user.email}"
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} not found"
    except Exception as e:
        return f"Error sending password reset email: {str(e)}"