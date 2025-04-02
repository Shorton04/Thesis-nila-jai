# Create a file: notifications/management/commands/test_email.py

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test email configuration'

    def handle(self, *args, **options):
        subject = 'Test Email from Business Permit System'
        message = 'This is a test email to verify the email configuration is working correctly.'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = ['your-test-email@example.com']  # Change this to your email

        try:
            send_mail(subject, message, from_email, recipient_list)
            self.stdout.write(self.style.SUCCESS('Email sent successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {e}'))