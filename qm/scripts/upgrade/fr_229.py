"""
FR #229 - Develop a dedicated "Running tasks" interface instead of pointing to the admin
This script adds the necessary permissions to the managed permissions table.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_229
"""

from config.models import Module, ModulePermission

def run():
    module = Module.objects.get(name='Running tasks')
    permission, created = ModulePermission.objects.get_or_create(
        module=module,
        action='Stop running task',
        defaults={
            'description': 'Can stop a running task.',
            'permission': 'qm.delete_tasksstatus',
        }
    )
    if created:
        print(f"Added permission")
    else:
        print(f"Permission already exists")