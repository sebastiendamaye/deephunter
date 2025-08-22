from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
from .models import Notification, UserNotification

NOTIFICATIONS_RECIPIENTS = settings.NOTIFICATIONS_RECIPIENTS

@receiver(post_save, sender=Notification)
def create_user_notifications(sender, instance, created, **kwargs):
    if created:
        users = User.objects.filter(
            Q(username__in=NOTIFICATIONS_RECIPIENTS[instance.level]['users']) |
            Q(groups__name__in=NOTIFICATIONS_RECIPIENTS[instance.level]['groups'])
        )
        user_notifications = [
            UserNotification(notification=instance, user=user)
            for user in users
        ]
        UserNotification.objects.bulk_create(user_notifications)
