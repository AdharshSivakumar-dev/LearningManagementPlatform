from lms.models import Notification, LMSUser
from asgiref.sync import sync_to_async
from django.core.mail import send_mail

@sync_to_async
def create_notification(user: LMSUser, message: str, link: str = None):
    Notification.objects.create(user=user, message=message, link=link)
    send_mail(
        subject="LMS Notification",
        message=f"{message}\n\nView details: {link}",
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )
