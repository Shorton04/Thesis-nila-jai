# notifications/tasks.py
from celery.schedules import crontab

from celery import shared_task, app
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


@shared_task
def send_template_email(subject, template_name, context, recipient_list):
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list
    )

    email.attach_alternative(html_content, "text/html")
    return email.send()

@shared_task
def send_deadline_reminders():
    from django.core.management import call_command
    call_command('send_deadline_reminders')

# In your Celery beat schedule (celery.py)
app.conf.beat_schedule = {
    'send-deadline-reminders-daily': {
        'task': 'your_app.tasks.send_deadline_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9:00 AM
    },
}