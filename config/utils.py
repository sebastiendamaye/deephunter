from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group, Permission

def check_group_permission(group_name, permission):
    """
    Check if a group has a specific permission.
    :param group_name: Name of the group
    :param permission: Permission string in the format 'app_label.codename'
    :return: True if the group has the permission, False otherwise
    """
    perm_app_label, perm_codename = permission.split('.')
    group = get_object_or_404(Group, name=group_name)
    permission = get_object_or_404(Permission, codename=perm_codename, content_type__app_label=perm_app_label)
    if permission in group.permissions.all():
        return True
    return False
