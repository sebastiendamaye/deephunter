"""
FR #251 - Add the settings permission in the managed permissions
This script adds the necessary permissions to the managed permissions table.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_251
"""

from config.models import Module, ModulePermission
from django.shortcuts import get_object_or_404

def run():

    modules_to_add = ['Dashboard', 'Analytics', 'Saved searches', 'Analytics Review', 'Campaigns', 'Endpoints',
                      'Timeline', 'Netview', 'Reports', 'Tools', 'Running tasks', 'Repos', 'Settings']

    permissions_to_add = [
        {
            "module": "Dashboard",
            "action": "View",
            "description": "Access the dashboard screen (welcome screen)",
            "permission": "dashboard.view_dashboard"
        }, {
            "module": "Analytics",
            "action": "View",
            "description": "View the details of a threat hunting analytic",
            "permission": "qm.view_analytic"
        }, {
            "module": "Analytics",
            "action": "Create new tags",
            "description": "Can create new tags from the analytics form.",
            "permission": "qm.add_tag"
        }, {
            "module": "Analytics",
            "action": "Create new threat names",
            "description": "Can create new threat names from the analytics form.",
            "permission": "qm.add_threatname"
        }, {
            "module": "Analytics",
            "action": "Create new threat actors",
            "description": "Can create new threat actors from the analytics form.",
            "permission": "qm.add_threatactor"
        }, {
            "module": "Analytics",
            "action": "Create new vulnerabilities",
            "description": "Can create new vulnerabilities from the analytics form.",
            "permission": "qm.add_vulnerability"
        }, {
            "module": "Analytics",
            "action": "Add",
            "description": "Add new Threat Hunting analytics",
            "permission": "qm.add_analytic"
        }, {
            "module": "Analytics",
            "action": "Delete",
            "description": "Delete Threat Hunting analytics",
            "permission": "qm.delete_analytic"
        }, {
            "module": "Analytics",
            "action": "Update",
            "description": "Update a threat hunting analytic",
            "permission": "qm.change_analytic"
        }, {
            "module": "Analytics",
            "action": "Bulk update",
            "description": "Update the status of several Threat Hunting analytics",
            "permission": "qm.bulk_update_analytics"
        }, {
            "module": "Analytics",
            "action": "Update status",
            "description": "Update the status of a threat hunting analytic",
            "permission": "qm.change_analytic_status"
        }, {
            "module": "Analytics",
            "action": "View trend/stats",
            "description": "Access the statistics (trend) of a threat hunting analytic",
            "permission": "qm.view_snapshot"
        }, {
            "module": "Analytics",
            "action": "Regenerate trend/stats",
            "description": "Regenerate the statistics of a Threat Hunting analytic",
            "permission": "qm.change_snapshot"
        }, {
            "module": "Analytics",
            "action": "Delete trend/stats",
            "description": "Delete statistics on analytics",
            "permission": "qm.delete_snapshot"
        }, {
            "module": "Analytics",
            "action": "Run query",
            "description": "Ability to run the query of a threat hunting analytic",
            "permission": "qm.run_query"
        }, {
            "module": "Analytics",
            "action": "View history",
            "description": "View the history of a threat hunting analytic",
            "permission": "qm.view_historicalanalytic"
        }, {
            "module": "Saved searches",
            "action": "View",
            "description": "Access saved searches",
            "permission": "qm.view_savedsearch"
        }, {
            "module": "Saved searches",
            "action": "Add",
            "description": "Add a new saved search",
            "permission": "qm.add_savedsearch"
        }, {
            "module": "Saved searches",
            "action": "Change",
            "description": "Change a saved search (if public or owner of a saved search)",
            "permission": "qm.change_savedsearch"
        }, {
            "module": "Saved searches",
            "action": "Delete",
            "description": "Delete a saved search (if public or owner of a saved search)",
            "permission": "qm.delete_savedsearch"
        }, {
            "module": "Analytics Review",
            "action": "View",
            "description": "View the reviews of a threat hunting analytic",
            "permission": "qm.view_review"
        }, {
            "module": "Analytics Review",
            "action": "Post review",
            "description": "Post a review when a threat hunting is in PENDING status",
            "permission": "qm.add_review"
        }, {
            "module": "Campaigns",
            "action": "View",
            "description": "View campaisgns",
            "permission": "qm.view_campaign"
        }, {
            "module": "Campaigns",
            "action": "Regenerate campaigns",
            "description": "Regenerate a campaign (e.g. in case the cron job failed)",
            "permission": "qm.change_campaign"
        }, {
            "module": "Endpoints",
            "action": "View",
            "description": "View endpoints (Endpoint report)",
            "permission": "qm.view_endpoint"
        }, {
            "module": "Timeline",
            "action": "View",
            "description": "Access the timeline module",
            "permission": "qm.view_timeline"
        }, {
            "module": "Netview",
            "action": "View",
            "description": "Access the netview module",
            "permission": "qm.view_netview"
        }, {
            "module": "Reports",
            "action": "View",
            "description": "View the reports menu",
            "permission": "qm.view_reports"
        }, {
            "module": "Tools",
            "action": "Access tools",
            "description": "Access the tools menu",
            "permission": "extensions.view_extensions"
        }, {
            "module": "Running tasks",
            "action": "See running tasks",
            "description": "Access the running tasks (% completion, status)",
            "permission": "qm.view_tasksstatus"
        }, {
            "module": "Running tasks",
            "action": "Stop running task",
            "description": "Can stop a running task.",
            "permission": "qm.delete_tasksstatus"
        }, {
            "module": "Repos",
            "action": "View",
            "description": "View a repository",
            "permission": "repos.view_repo"
        }, {
            "module": "Repos",
            "action": "Add",
            "description": "Add a repository",
            "permission": "repos.add_repo"
        }, {
            "module": "Repos",
            "action": "Update",
            "description": "Update the details of a repository (e.g. URL)",
            "permission": "repos.change_repo"
        }, {
            "module": "Repos",
            "action": "Check",
            "description": "Can check a repository",
            "permission": "repos.check"
        }, {
            "module": "Repos",
            "action": "Import",
            "description": "Can import threat hunting analytics from a repository",
            "permission": "repos.import"
        }, {
            "module": "Repos",
            "action": "Delete",
            "description": "Delete a repository",
            "permission": "repos.delete_repo"
        }, {
            "module": "Settings",
            "action": "Change connectors settings",
            "description": "Can change the connectors settings.",
            "permission": "connectors.change_connectorconf"
        }, {
            "module": "Settings",
            "action": "Set permissions",
            "description": "Can change the permissions in the settings menu.",
            "permission": "config.change_modulepermission"
        },
    ]

    for module_to_add in modules_to_add:
        module, created = Module.objects.get_or_create(name=module_to_add)
        if created:
            print(f"Created '{module_to_add}' module")
        else:
            print(f"'{module_to_add}' module already exists")


    for perm in permissions_to_add:
        permission, created = ModulePermission.objects.get_or_create(
            module=get_object_or_404(Module, name=perm['module']),
            action=perm['action'],
            defaults={
                'description': perm['description'],
                'permission': perm['permission'],
            }
        )
        if created:
            print(f"Added permission: {perm['action']} ({perm['permission']}) for module '{perm['module']}'")
        else:
            print(f"Permission already exists: {perm['action']} ({perm['permission']}) for module '{perm['module']}'")