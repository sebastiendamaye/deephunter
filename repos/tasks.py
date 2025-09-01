from celery import shared_task
from notifications.utils import add_info_notification, add_success_notification, add_debug_notification
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404
from django.db import transaction
from .models import Repo, RepoAnalytic
from qm.models import Analytic, Category, TargetOs, ThreatName, ThreatActor, Vulnerability, MitreTechnique, TasksStatus
from connectors.models import Connector
import requests
from json.decoder import JSONDecodeError
from pathlib import Path
import time
from .utils import re_escape, is_imported

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module

PROXY = settings.PROXY
REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST = settings.REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST
REPO_IMPORT_DEFAULT_STATUS = settings.REPO_IMPORT_DEFAULT_STATUS
REPO_IMPORT_DEFAULT_RUN_DAILY = settings.REPO_IMPORT_DEFAULT_RUN_DAILY

DEBUG = False

@shared_task()
def import_repo_task(repo_id, mode, selected_analytics=None):

    # mode: check|import
    repo = get_object_or_404(Repo, pk=repo_id)
    add_info_notification(f'check repo task started: {repo.name}')

    if DEBUG:
        add_debug_notification(f'Starting import repo task: {repo.name} (mode: {mode})')

    if "github.com" in repo.url:
        contents = all_connectors.get('github').get_github_contents(repo.url)
    elif "bitbucket.org" in repo.url:
        contents = all_connectors.get('bitbucket').get_bitbucket_contents(repo.url)
    nb_analytics = 0

    # We delete previous ref in RepoAnalytic related to this repo
    RepoAnalytic.objects.filter(repo=repo).delete()

    celery_status = get_object_or_404(TasksStatus, taskname = f"import_repo_{repo_id}")
    if DEBUG:
        add_debug_notification(f'Found celery task {celery_status.taskname}')

    for content in contents:

        if DEBUG:
            add_debug_notification(f'Processing {content.get("name")} (will be ignored if not JSON file)')

        # We are only interested in JSON files on the repo
        if content.get('name').endswith('.json'):

            nb_analytics += 1
            report = []
            stop = False
            update_analytic = False

            results = requests.get(
                content.get('download_url'),
                proxies=PROXY
            )
            
            if DEBUG:
                add_debug_notification(f'Results: {results}')

            # Validate the JSON format
            imported_analytic = {}
            try:
                imported_analytic = results.json()
                if DEBUG:
                    add_debug_notification(f'Successfully got results in JSON: {imported_analytic}')

            except JSONDecodeError as e:
                report.append({"type": "error", "message": f"JSON format error: {str(e)}"})
                stop = True
                if DEBUG:
                    add_debug_notification(f'Invalid JSON. STOP')

            # Check mandatory keys
            if "name" in imported_analytic:
                analytic_name = imported_analytic['name'].strip()
                # check if analytic exists for this repo and this name
                if is_imported(analytic_name, repo):
                    update_analytic = True
                    if DEBUG:
                        add_debug_notification(f'Analytic found with same name: UPDATE operation')
            else:
                # if "name" key is missing, we extract the name from the JSON file (without *.json extension)
                analytic_name = Path(content.get('name')).stem
                report.append({"type": "error", "message": "Missing mandatory field: name"})
                stop = True
                if DEBUG:
                    add_debug_notification(f'Name key missing. STOP')

            if not "query" in imported_analytic:
                report.append({"type": "error", "message": "Missing mandatory field: query"})
                stop = True
                if DEBUG:
                    add_debug_notification(f'Query key missing. STOP')
            
            if not "connector" in imported_analytic:
                report.append({"type": "error", "message": "Missing mandatory field: connector"})
                stop = True
                if DEBUG:
                    add_debug_notification(f'Connector key missing. STOP')

            # If connector doesn't exist, critical error, we stop.
            if not stop:
                if DEBUG:
                    add_debug_notification(f'Checking connector.')
                try:
                    connector = get_object_or_404(Connector, name__iexact=imported_analytic['connector'].strip())
                except Http404 as e:
                    report.append({"type": "error", "message": str(e)})
                    stop = True

            if not stop:
                if DEBUG:
                    add_debug_notification(f'Checking category.')
                if "category" in imported_analytic:
                    try:
                        category = get_object_or_404(Category, name__iexact=imported_analytic['category'].strip())
                    except Http404 as e:
                        if REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST['category'].lower() == 'true':
                            # We create the missing category if setting set to create and don't log an error
                            category = Category(name=imported_analytic['category'].strip())
                            category.save()
                            report.append({"type": "info", "message": f"Category '{imported_analytic['category'].strip()}' does not exist. It has been created."})
                        else:
                            # if set to false, we set the category to null
                            category = None
                            report.append({"type": "info", "message": f"Category '{imported_analytic['category'].strip()}' does not exist. Analytic will be created without category."})
                else:
                    category = None
                    report.append({"type": "info", "message": "Category key not found in JSON. Analytic will be created without category."})

            if not stop:
                # fix out of band confidence
                if DEBUG:
                    add_debug_notification(f'Checking Confidence.')
                confidence = int(imported_analytic['confidence']) if "confidence" in imported_analytic else 1
                if confidence < 1 or confidence > 4:
                    confidence = 1
                    report.append({"type": "info", "message": f"Confidence '{imported_analytic['confidence']}' is out of bounds. It has been set to 1."})
                # fix out of band relevance
                if DEBUG:
                    add_debug_notification(f'Checking relevance.')
                relevance = int(imported_analytic['relevance']) if "relevance" in imported_analytic else 1
                if relevance < 1 or relevance > 4:
                    relevance = 1
                    report.append({"type": "info", "message": f"Relevance '{imported_analytic['relevance']}' is out of bounds. It has been set to 1."})

                try:

                    # We try to save the analytic
                    if update_analytic:
                        # If the analytic already exists in this repo, we update all fields but "status" and "run_daily" (as they may have been customized already)
                        analytic = get_object_or_404(Analytic, name=analytic_name, repo=repo)
                        if DEBUG:
                            add_debug_notification(f'UPDATE Analytic object: {analytic} -- repo: {repo}.')
                        analytic.description = re_escape(imported_analytic['description']) if "description" in imported_analytic else "",
                        analytic.notes = re_escape(imported_analytic['notes']) if "notes" in imported_analytic else "",
                        analytic.confidence = confidence,
                        analytic.relevance = relevance,
                        analytic.query = re_escape(imported_analytic['query']),
                        analytic.columns = re_escape(imported_analytic['columns']) if "columns" in imported_analytic else "",
                        analytic.emulation_validation = re_escape(imported_analytic['emulation_validation']) if "emulation_validation" in imported_analytic else "",
                        analytic.references = imported_analytic['references'] if "references" in imported_analytic else "",
                    else:
                        # if the analytic doesn't exist yet, we create it
                        if DEBUG:
                            add_debug_notification(f'CREATE Analytic object.')
                        analytic = Analytic(
                            name = imported_analytic['name'].strip(),
                            description = re_escape(imported_analytic['description']) if "description" in imported_analytic else "",
                            notes = re_escape(imported_analytic['notes']) if "notes" in imported_analytic else "",
                            status = REPO_IMPORT_DEFAULT_STATUS,
                            confidence = confidence,
                            relevance = relevance,
                            category = category,
                            repo = repo,
                            connector = connector,
                            query = re_escape(imported_analytic['query']),
                            columns = re_escape(imported_analytic['columns']) if "columns" in imported_analytic else "",
                            emulation_validation = re_escape(imported_analytic['emulation_validation']) if "emulation_validation" in imported_analytic else "",
                            references = imported_analytic['references'] if "references" in imported_analytic else "",
                            run_daily = REPO_IMPORT_DEFAULT_RUN_DAILY
                        )

                    # if we are in import mode and the analytic is selected to be imported
                    if mode == "import" and content.get('name') in selected_analytics:
                        # if mode is import, we really save the analytic
                        if DEBUG:
                            add_debug_notification(f'MODE IMPORT. We save.')
                        analytic.save()
                    else:
                        # If mode is check, we just want to validate the analytic without saving it
                        if DEBUG:
                            add_debug_notification(f'MODE CHECK. We validate.')
                        analytic.full_clean()

                except ValidationError as e:
                    report.append({"type": "error", "message": e.message_dict})
                    stop = True
                    if DEBUG:
                        add_debug_notification(f'VALIDATION ERROR {report}.')

                if not stop:

                    # If the analytic is saved, we can now add the M2M fields

                    if mode == "import":

                        if "target_os" in imported_analytic:
                            if DEBUG:
                                add_debug_notification('MODE import. M2M Target OS.')
                            for os in imported_analytic['target_os']:
                                try:
                                    target_os = get_object_or_404(TargetOs, name=os)
                                    analytic.target_os.add(target_os)
                                except Exception as e:
                                    # We never create target OS. If missing, we just ignore target OS
                                    report.append({"type": "info", "message": f"Missing target OS: {str(e)}"})
                        else:
                            report.append({"type": "info", "message": "Missing target OS in JSON. Analytic created without target OS"})

                        if "mitre_techniques" in imported_analytic:
                            if DEBUG:
                                add_debug_notification('MODE import. M2M Mitre Techniques.')
                            for mitre_technique in imported_analytic['mitre_techniques']:
                                try:
                                    mitre_technique = get_object_or_404(MitreTechnique, mitre_id=mitre_technique)
                                    analytic.mitre_techniques.add(mitre_technique)
                                except Exception as e:
                                    # We never create MITRE techniques. If missing, we just ignore MITRE techniques
                                    report.append({"type": "info", "message": f"Missing MITRE Technique: {str(e)}"})
                        else:
                            report.append({"type": "info", "message": "Missing MITRE Techniques in JSON. Analytic created without MITRE Techniques"})

                        if "threats" in imported_analytic:
                            if DEBUG:
                                add_debug_notification('MODE import. M2M Threats.')
                            for threat in imported_analytic['threats']:
                                try:
                                    threat = get_object_or_404(ThreatName, name=threat)
                                    analytic.threats.add(threat)
                                except Http404 as e:
                                    if REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST['threats'].lower() == 'true':
                                        threat = ThreatName(name=threat)
                                        threat.save()
                                        report.append({"type": "info", "message": f"Threat '{threat}' does not exist. It's been created."})
                                    else:
                                        report.append({"type": "info", "message": f"Threat '{threat}' does not exist. Analytic created without this threat."})
                        else:
                            report.append({"type": "info", "message": f"Missing threats in JSON. Analytic created without threats."})

                        if "actors" in imported_analytic:
                            if DEBUG:
                                add_debug_notification('MODE import. M2M Threat Actors.')
                            for actor in imported_analytic['actors']:
                                try:
                                    actor = get_object_or_404(ThreatActor, name=actor)
                                    analytic.actors.add(actor)
                                except Http404 as e:
                                    if REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST['actors'].lower() == 'true':
                                        actor = ThreatActor(name=actor)
                                        actor.save()
                                        report.append({"type": "info", "message": f"Threat actor '{actor}' does not exist. It's been created."})
                                    else:
                                        report.append({"type": "info", "message": f"Threat actor '{actor}' does not exist. Analytic created without this threat actor."})
                        else:
                            report.append({"type": "info", "message": f"Missing actors in JSON. Analytic created without actors."})

                        if "vulnerabilities" in imported_analytic:
                            if DEBUG:
                                add_debug_notification('MODE import. M2M Vulnerabilities.')
                            for vulnerability in imported_analytic['vulnerabilities']:
                                try:
                                    vulnerability = get_object_or_404(Vulnerability, name=vulnerability)
                                    analytic.vulnerabilities.add(vulnerability)
                                except Http404 as e:
                                    if REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST['vulnerabilities'].lower() == 'true':
                                        vulnerability = Vulnerability(name=vulnerability)
                                        vulnerability.save()
                                        report.append({"type": "info", "message": f"Vulnerability '{vulnerability}' does not exist. It's been created."})
                                    else:
                                        report.append({"type": "info", "message": f"Vulnerability '{vulnerability}' does not exist. Analytic created without this vulnerability."})
                        else:
                            report.append({"type": "info", "message": "Missing vulnerabilities in JSON. Analytic created without vulnerabilities."})

                    else: # mode check

                        with transaction.atomic():
                            analytic.save()  # Required to assign a PK before M2M can be added
                            if DEBUG:
                                add_debug_notification('MODE check. We saved the analytic (rollback later).')


                            if "target_os" in imported_analytic:
                                if DEBUG:
                                    add_debug_notification('MODE check. M2M Target OS.')
                                for os in imported_analytic['target_os']:
                                    try:
                                        target_os = get_object_or_404(TargetOs, name=os)
                                        analytic.target_os.add(target_os)
                                    except Exception as e:
                                        # We never create target OS. If missing, we just ignore target OS
                                        report.append({"type": "info", "message": f"Missing target OS: {str(e)}"})
                            else:
                                report.append({"type": "info", "message": "Missing target OS in JSON. Analytic created without target OS"})

                            if "mitre_techniques" in imported_analytic:
                                if DEBUG:
                                    add_debug_notification('MODE check. M2M Mitre Techniques.')
                                for mitre_technique in imported_analytic['mitre_techniques']:
                                    try:
                                        mitre_technique = get_object_or_404(MitreTechnique, mitre_id=mitre_technique)
                                        analytic.mitre_techniques.add(mitre_technique)
                                    except Exception as e:
                                        # We never create MITRE techniques. If missing, we just ignore MITRE techniques
                                        report.append({"type": "info", "message": f"Missing MITRE Technique: {str(e)}"})
                            else:
                                report.append({"type": "info", "message": "Missing MITRE Techniques in JSON. Analytic created without MITRE Techniques"})

                            if "threats" in imported_analytic:
                                if DEBUG:
                                    add_debug_notification('MODE check. M2M Threats.')
                                for threat in imported_analytic['threats']:
                                    try:
                                        threat = get_object_or_404(ThreatName, name=threat)
                                        analytic.threats.add(threat)
                                    except Http404 as e:
                                        if REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST['threats'].lower() == 'true':
                                            threat = ThreatName(name=threat)
                                            threat.save()
                                            report.append({"type": "info", "message": f"Threat '{threat}' does not exist. It's been created."})
                                        else:
                                            report.append({"type": "info", "message": f"Threat '{threat}' does not exist. Analytic created without this threat."})
                            else:
                                report.append({"type": "info", "message": "Missing threats in JSON. Analytic created without threats."})

                            if "actors" in imported_analytic:
                                if DEBUG:
                                    add_debug_notification('MODE check. M2M threat actors.')
                                for actor in imported_analytic['actors']:
                                    try:
                                        actor = get_object_or_404(ThreatActor, name=actor)
                                        analytic.actors.add(actor)
                                    except Http404 as e:
                                        if REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST['actors'].lower() == 'true':
                                            actor = ThreatActor(name=actor)
                                            actor.save()
                                            report.append({"type": "info", "message": f"Threat actor '{actor}' does not exist. It's been created."})
                                        else:
                                            report.append({"type": "info", "message": f"Threat actor '{actor}' does not exist. Analytic created without this threat actor."})
                            else:
                                report.append({"type": "info", "message": "Missing actors in JSON. Analytic created without actors."})

                            if "vulnerabilities" in imported_analytic:
                                if DEBUG:
                                    add_debug_notification('MODE check. M2M Vulnerabilities.')
                                for vulnerability in imported_analytic['vulnerabilities']:
                                    try:
                                        vulnerability = get_object_or_404(Vulnerability, name=vulnerability)
                                        analytic.vulnerabilities.add(vulnerability)
                                    except Http404 as e:
                                        if REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST['vulnerabilities'].lower() == 'true':
                                            vulnerability = Vulnerability(name=vulnerability)
                                            vulnerability.save()
                                            report.append({"type": "info", "message": f"Vulnerability '{vulnerability}' does not exist. It's been created."})
                                        else:
                                            report.append({"type": "info", "message": f"Vulnerability '{vulnerability}' does not exist. Analytic created without this vulnerability."})
                            else:
                                report.append({"type": "info", "message": "Missing vulnerabilities in JSON. Analytic created without vulnerabilities."})


                            # This silently rolls back at the end
                            transaction.set_rollback(True)
                            if DEBUG:
                                add_debug_notification('MODE check. ROLLBACK DONE.')


            repoanalytic = RepoAnalytic(
                repo = repo,
                name = analytic_name,
                url = content.get('download_url'),
                report = report,
                is_valid = False if stop else True,
            )
            repoanalytic.save()
            if DEBUG:
                add_debug_notification('Added analytic to RepoAnalytic.')

            # We update the progress of the task
            celery_status.progress = int((nb_analytics / len(contents)) * 100)
            celery_status.save()
            if DEBUG:
                add_debug_notification(f'Celery task status updated: {celery_status.progress}.')

    # last_check_date will always be updated (even with import)
    repo.last_check_date = datetime.now()
    if mode == "import":
        repo.last_import_date = datetime.now()
    repo.save()

    if DEBUG:
        add_debug_notification(f'Dates updated in Repo.')

    # We delete the task
    celery_status.delete()
    add_success_notification(f'check repo task completed: {repo.name}')

    if DEBUG:
        add_debug_notification(f'TASK COMPLETE.')
