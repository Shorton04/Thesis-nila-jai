# notifications/management/commands/send_test_notification.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.utils import create_notification

User = get_user_model()


class Command(BaseCommand):
    help = 'Send a test notification to a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the recipient')
        parser.add_argument('--title', type=str, default='Test Notification', help='Notification title')
        parser.add_argument('--message', type=str, default='This is a test notification.', help='Notification message')
        parser.add_argument('--type', type=str, default='info',
                            help='Notification type (info, success, warning, error, etc.)')

    def handle(self, *args, **options):
        username = options['username']
        title = options['title']
        message = options['message']
        notification_type = options['type']

        try:
            user = User.objects.get(username=username)
            notification = create_notification(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            self.stdout.write(self.style.SUCCESS(f'Notification sent to {username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} does not exist'))