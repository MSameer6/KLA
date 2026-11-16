from django.conf import settings
from django.core.mail import send_mail

from .models import ActivityLog, Client, ClientNotification, TaxCase


def record_activity(user, action, description, client=None, tax_case=None):
    return ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        client=client,
        tax_case=tax_case,
    )


def notify_client(client: Client, title: str, message: str, tax_case: TaxCase | None = None):
    notification = ClientNotification.objects.create(
        client=client,
        tax_case=tax_case,
        title=title,
        message=message,
    )
    if client.email:
        send_mail(
            subject=f"Khan Law Associates: {title}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[client.email],
            fail_silently=False,
        )
    return notification
