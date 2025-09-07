from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from .models import Notification, UserNotification
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from datetime import datetime, timedelta

@login_required
def show_notifications(request):
    notifications = UserNotification.objects.filter(user=request.user, is_read=False).order_by('-notification__created_at')
    context = { "notifications": notifications }
    return render(request, 'notifications.html', context)

@login_required
def get_number_notifications(request):
    notifications = UserNotification.objects.filter(user=request.user, is_read=False)
    return HttpResponse(notifications.count() if notifications else "")

@login_required
def mark_read_all(request):
    notifications = UserNotification.objects.filter(user=request.user, is_read=False)
    notifications.update(is_read=True)
    return HttpResponseRedirect(reverse('show_notifications'))

@login_required
def mark_read(request, notification_id):
    notification = get_object_or_404(UserNotification, pk=notification_id, user=request.user)
    notification.is_read=True
    notification.save()
    return HttpResponseRedirect(reverse('show_notifications'))

@login_required
def get_notifications(request):
    # Since notifications are polled every 10s, we only want to show notifications
    # that are younger than 10 seconds ago
    usernotifications = UserNotification.objects.filter(
        user=request.user,
        is_read=False,
        notification__created_at__gte=datetime.now() - timedelta(seconds=10)
    ).order_by('-notification__created_at')
    notifications_list = [
        {
            "id": n.id,
            "message": n.notification.message,
            "level": n.notification.level,
        }
        for n in usernotifications
    ]
    return JsonResponse({"notifications": notifications_list})
