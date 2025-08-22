from django.conf import settings
from notifications.models import Notification
from datetime import datetime, timedelta
from notifications.utils import add_debug_notification

AUTO_DELETE_NOTIFICATIONS_AFTER = settings.AUTO_DELETE_NOTIFICATIONS_AFTER
DEBUG = False

def run():
    total_deleted = 0
    for level, days in AUTO_DELETE_NOTIFICATIONS_AFTER.items():
        expiry_date = datetime.now() - timedelta(days=days)
        expired_notifications = Notification.objects.filter(level=level, created_at__lt=expiry_date)
        count = expired_notifications.count()
        expired_notifications.delete()
        total_deleted += count
        if DEBUG:
            add_debug_notification(f"delete_notifications script / Deleted {count} notifications for level '{level}' older than {days} days.")
    if DEBUG:
        add_debug_notification(f"delete_notifications script / Total deleted: {total_deleted}")
