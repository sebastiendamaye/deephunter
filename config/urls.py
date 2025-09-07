from django.urls import path
from . import views

urlpatterns = [
    path('deephunter-settings/', views.deephunter_settings, name='deephunter_settings'),
    path('permissions/', views.permissions, name='permissions'), 
    path('update-permission/<int:group_id>/<int:permission_id>/', views.update_permission, name='update_permission'),
]
