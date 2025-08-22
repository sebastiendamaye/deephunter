from .models import Notification
from django.shortcuts import get_object_or_404

def add_notification(message, level, uid=None):
    """
    level: debug | info | success | warning | error
    uid: update_available_deephunter | update_available_mitre | tokenexpires_sentinelone | tokenexpires_microsoftsentinel
    """
    notification = Notification(
        message=message,
        level=level,
        uid=uid
    )
    notification.save()

def add_debug_notification(message, uid=None):
    add_notification(message, level='debug', uid=uid)

def add_info_notification(message, uid=None):
    add_notification(message, level='info', uid=uid)

def add_success_notification(message, uid=None):
    add_notification(message, level='success', uid=uid)

def add_warning_notification(message, uid=None):
    add_notification(message, level='warning', uid=uid)

def add_error_notification(message, uid=None):
    add_notification(message, level='error', uid=uid)

def del_notification_by_uid(uid):
    """
    uid: update_available_deephunter | update_available_mitre | tokenexpires_sentinelone | tokenexpires_microsoftsentinel
    """
    try:
        notification = get_object_or_404(Notification, uid=uid)
        notification.delete()
    except:
        pass
    