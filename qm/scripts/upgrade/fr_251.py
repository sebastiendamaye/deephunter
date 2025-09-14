"""
FR #251 - Add the settings permission in the managed permissions
This script adds the necessary permissions to the managed permissions table.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_251
"""

from config.models import Module, ModulePermission

def run():
    module, created = Module.objects.get_or_create(name='Settings')
    if created:
        print("Created 'Settings' module")
    else:
        print("'Settings' module already exists")

    permissions_to_add = [
        {
            'action': 'Change connectors settings',
            'description': 'Can change the connectors settings.',
            'permission': 'connectors.change_connectorconf',
        },
        {
            'action': 'Set permissions',
            'description': 'Can change the permissions in the settings menu.',
            'permission': 'config.change_modulepermission',
        },
    ]

    for perm in permissions_to_add:
        permission, created = ModulePermission.objects.get_or_create(
            module=module,
            action=perm['action'],
            defaults={
                'description': perm['description'],
                'permission': perm['permission'],
            }
        )
        if created:
            print(f"Added permission: {perm['action']} ({perm['permission']})")
        else:
            print(f"Permission already exists: {perm['action']} ({perm['permission']})")