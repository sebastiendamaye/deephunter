from django.db import models
from django.contrib.auth.models import User

class Notification(models.Model):
    """
    uid is used to remove notifications if no longer relevant
    (e.g. notif sent to all users to inform that deephunter update was available.
    Once it's been updated, notifications should be automatically removed)
      - update_available_deephunter
      - update_available_mitre
      - tokenexpires_sentinelone
      - tokenexpires_microsoftsentinel
    """

    LEVEL_CHOICES = [
        ('debug', 'DEBUG'),
        ('info', 'INFO'),
        ('success', 'SUCCESS'),
        ('warning', 'WARNING'),
        ('error', 'ERROR'),
    ]

    message = models.TextField()
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    uid = models.CharField(max_length=50, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.message[:100]}..."

class UserNotification(models.Model):
    """
    User notifications will be populated automatically by signals when a new notification is created
    """
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.notification.message[:100]}..."
