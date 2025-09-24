from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from .models import Module, ModulePermission
from qm.models import TasksStatus
from notifications.utils import add_debug_notification, add_error_notification, add_success_notification
from .utils import check_group_permission
from celery import current_app

DEBUG = settings.DEBUG

@login_required
def deephunter_settings(request):
    return render(request, 'deephunter_settings.html')

@login_required
@permission_required('config.change_modulepermission', raise_exception=True)
def permissions(request):
    groups = Group.objects.order_by('name')
    modules = []
    for module in Module.objects.all():
        permissions = []
        for permission in module.modulepermission_set.all():
            group_permission = []
            for group in groups:
                group_permission.append({
                    'group_id': group.id,
                    'name': group.name,
                    'has_perm': check_group_permission(group.name, permission.permission),
                })
            permissions.append({
                'permission_id': permission.id,
                'action': permission.action,
                'description': permission.description,
                'permission': permission.permission,
                'groups': group_permission,
            })
        modules.append({
            'module': module.name,
            'permissions': permissions,
        })

    context = {
        'groups': [group.name for group in Group.objects.order_by('name')],
        'modules': modules,
    }
    return render(request, 'permissions.html', context)

@login_required
@permission_required('config.change_modulepermission', raise_exception=True)
def update_permission(request, group_id, permission_id):

    group = get_object_or_404(Group, id=group_id)
    permission = get_object_or_404(ModulePermission, id=permission_id)
    group_permission = check_group_permission(group.name, permission.permission)

    perm_app_label, perm_codename = permission.permission.split('.')
    perm = get_object_or_404(Permission, codename=perm_codename, content_type__app_label=perm_app_label)
    if group_permission:
        # Remove permission
        group.permissions.remove(perm)
        if DEBUG:
            add_debug_notification(f"Removed {permission.permission} from {group.name}")
    else:
        # Add permission
        group.permissions.add(perm)
        if DEBUG:
            add_debug_notification(f"Added {permission.permission} to {group.name}")
    return HttpResponse(status=204)

@login_required
@permission_required('qm.delete_tasksstatus', raise_exception=True)
def running_tasks(request):
    return render(request, 'running_tasks.html')

@login_required
@permission_required('qm.delete_tasksstatus', raise_exception=True)
def running_tasks_table(request):
    context = {
        'running_tasks': TasksStatus.objects.all(),
    }
    return render(request, 'partials/running_tasks_table.html', context)

@login_required
@permission_required('qm.delete_tasksstatus', raise_exception=True)
def task_status(request, task_id):
    task_status = get_object_or_404(TasksStatus, pk=task_id)
    code = f"{round(task_status.progress)}%"
    if task_status.taskid:
        code += f' | <button class="buttonred" hx-get="/config/stop-running-task/{task_status.id}/" hx-swap="outerHTML">Stop</button>'
    return HttpResponse(code)

@login_required
@permission_required('qm.delete_tasksstatus', raise_exception=True)
def stop_running_task(request, task_id):
    try:
        task = get_object_or_404(TasksStatus, pk=task_id)
        # without signal='SIGKILL', the task is not cancelled immediately
        current_app.control.revoke(task.taskid, terminate=True, signal='SIGKILL')
        # delete task in DB
        celery_status = get_object_or_404(TasksStatus, taskid=task.taskid)
        celery_status.delete()
        add_success_notification(f'Celery Task {task.taskname} terminated')
        return HttpResponse('Task terminated')
    except Exception as e:
        add_error_notification(f'Error terminating Celery Task: {e}')
        return HttpResponse(f'Error terminating Celery Task: {e}')
