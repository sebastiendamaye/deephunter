"""
FR #213 - Replace admin form with dedicated UI to create/update analytics
This script adds the necessary permissions to allow creating
new tags, threat names, threat actors, vulnerabilities from the analytic form.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_213
"""

from config.models import Module, ModulePermission

def run():
    if Module.objects.filter(name='Analytics').exists():
        module = Module.objects.get(name='Analytics')
        print("'Analytics' module already exists")
    else:
        module = Module.objects.get(name='Analytic')
        module.name='Analytics'
        module.save()
        print("Renamed 'Analytic' module to 'Analytics'")

    permissions_to_add = [
        {
            'action': 'Create new tags',
            'description': 'Can create new tags from the analytics form.',
            'permission': 'qm.add_tag',
        },
        {
            'action': 'Create new threat names',
            'description': 'Can create new threat names from the analytics form.',
            'permission': 'qm.add_threatname',
        },
        {
            'action': 'Create new threat actors',
            'description': 'Can create new threat actors from the analytics form.',
            'permission': 'qm.add_threatactor',
        },
        {
            'action': 'Create new vulnerabilities',
            'description': 'Can create new vulnerabilities from the analytics form.',
            'permission': 'qm.add_vulnerability',
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