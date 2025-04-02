# notifications/management/commands/send_deadline_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from applications.models import ApplicationRevision, ApplicationAssessment
from notifications.utils import send_deadline_reminder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send deadline reminder emails for applications with deadlines tomorrow'

    def handle(self, *args, **options):
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)

        self.stdout.write(f"Checking for deadlines on {tomorrow}")

        # Check for revision deadlines
        revisions = ApplicationRevision.objects.filter(
            deadline__date=tomorrow,
            is_resolved=False
        )

        revision_count = 0
        for revision in revisions:
            if revision.application.applicant:
                success = send_deadline_reminder(
                    user=revision.application.applicant,
                    application=revision.application,
                    deadline=revision.deadline,
                    revision=revision
                )
                if success:
                    revision_count += 1

        # Check for payment deadlines
        assessments = ApplicationAssessment.objects.filter(
            payment_deadline__date=tomorrow,
            is_paid=False
        )

        assessment_count = 0
        for assessment in assessments:
            if assessment.application.applicant:
                success = send_deadline_reminder(
                    user=assessment.application.applicant,
                    application=assessment.application,
                    deadline=assessment.payment_deadline,
                    assessment=assessment
                )
                if success:
                    assessment_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sent {revision_count} revision deadline reminders and {assessment_count} payment deadline reminders"
        ))