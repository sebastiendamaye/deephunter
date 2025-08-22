from django.contrib import admin
from .models import Notification, UserNotification

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('message', 'level', 'uid', 'created_at')
    list_filter = ['level', 'uid', 'created_at']
    search_fields = ['message']

class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('notification__message', 'user__username', 'is_read', 'read_at')
    list_filter = ['user__username', 'is_read', 'read_at']
    search_fields = ['notification__message']

admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)