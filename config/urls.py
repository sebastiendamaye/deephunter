from django.urls import path
from . import views

urlpatterns = [
    path('deephunter-settings/', views.deephunter_settings, name='deephunter_settings'),
    path('permissions/', views.permissions, name='permissions'), 
    path('update-permission/<int:group_id>/<int:permission_id>/', views.update_permission, name='update_permission'),
    path('running-tasks/', views.running_tasks, name='running_tasks'),
    path('running-tasks-table/', views.running_tasks_table, name='running_tasks_table'),
    path('task-status/<str:task_id>/', views.task_status, name='task_status'),
    path('stop-running-task/<str:task_id>/', views.stop_running_task, name='stop_running_task'),
]
