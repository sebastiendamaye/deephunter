from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from .models import Module, ModulePermission
from notifications.utils import add_debug_notification
from .utils import check_group_permission

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
