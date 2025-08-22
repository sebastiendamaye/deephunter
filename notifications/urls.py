from django.urls import path
from . import views

urlpatterns = [
    path('', views.show_notifications, name='show_notifications'),
    path('get_number_notifications/', views.get_number_notifications, name='get_number_notifications'),
    path('mark_read/all/', views.mark_read_all, name='mark_read_all'),
    path('mark_read/<int:notification_id>/', views.mark_read, name='mark_read'),
]
