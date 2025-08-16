from django.shortcuts import render, get_object_or_404, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404
from django.db import transaction
from .models import Repo
from .forms import RepoForm
from qm.models import Analytic, Category, MitreTechnique, ThreatName, ThreatActor, TargetOs, Vulnerability
from connectors.models import Connector
import requests
import json
from json.decoder import JSONDecodeError
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
import base64

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module


PROXY = settings.PROXY
REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST = settings.REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST
REPO_SYNC_DEFAULT_STATUS = settings.REPO_SYNC_DEFAULT_STATUS
REPO_SYNC_DEFAULT_RUN_DAILY = settings.REPO_SYNC_DEFAULT_RUN_DAILY

@login_required
def list_repos(request):
    context = {"repos": Repo.objects.all()}
    return render(request, "list_repos.html", context)

@login_required
def sync_repo_select_analytics(request, repo_id):
    repo = get_object_or_404(Repo, pk=repo_id)
    if "github.com" in repo.url:
        contents = all_connectors.get('github').get_github_contents(repo.url)
    elif "bitbucket.org" in repo.url:
        contents = all_connectors.get('bitbucket').get_bitbucket_contents(repo.url)
    context = {
        "repo": repo,
        "contents": contents,
    }
    return render(request, 'sync_repo_select_analytics.html', context)

@login_required
def preview(request, url):
    # Add back padding if necessary
    padding = '=' * (-len(url) % 4)
    url += padding
    results = requests.get(
        unquote(base64.urlsafe_b64decode(url).decode()),
        proxies=PROXY
    )
    return HttpResponse(results.json() if results.headers.get('Content-Type') == 'application/json' else results.text)

def re_escape(s):
    return s.encode('unicode_escape').decode('utf-8')

@login_required
@require_http_methods(["GET", "POST"])
def sync_repo(request, repo_id, mode):
    # mode: check|sync
    repo = get_object_or_404(Repo, pk=repo_id)
    if "github.com" in repo.url:
        contents = all_connectors.get('github').get_github_contents(repo.url)
    elif "bitbucket.org" in repo.url:
        contents = all_connectors.get('bitbucket').get_bitbucket_contents(repo.url)
    analytics = []
    nb_analytics = 0
    nb_analytics_errors = 0
    nb_analytics_valid = 0

    for content in contents:
        if content.get('name').endswith('.json'):
            if mode == "check" or (mode == "sync" and content.get('name') in request.POST.getlist('analytics')):

                nb_analytics += 1
                errors = []
                infos = []
                stop = False

                results = requests.get(
                    content.get('download_url'),
                    proxies=PROXY
                )
                
                # Validate the JSON format
                try:
                    imported_analytic= results.json()
                except JSONDecodeError as e:
                    errors.append(f"JSON format error: {str(e)}")
                    stop = True

                # Check mandatory keys
                if "name" in imported_analytic:
                    analytic_name = imported_analytic['name'].strip()
                else:
                    # if "name" key is missing, we extract the name from the JSON file (without *.json extension)
                    analytic_name = Path(content.get('name')).stem
                    errors.append("Missing mandatory field: name")
                    stop = True

                if not "query" in imported_analytic:
                    errors.append("Missing mandatory field: query")
                    stop = True
                
                if not "connector" in imported_analytic:
                    errors.append("Missing mandatory field: connector")
                    stop = True

                # If connector doesn't exist, critical error, we stop
                if not stop:
                    try:
                        connector = get_object_or_404(Connector, name__iexact=imported_analytic['connector'].strip())
                    except Http404 as e:
                        errors.append(str(e))
                        stop = True

                if not stop:
                    if "category" in imported_analytic:
                        try:
                            category = get_object_or_404(Category, name__iexact=imported_analytic['category'].strip())
                        except Http404 as e:
                            if REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST['category'].lower() == 'true':
                                # We create the missing category if setting set to create and don't log an error
                                category = Category(name=imported_analytic['category'].strip())
                                category.save()
                                infos.append(f"Category '{imported_analytic['category'].strip()}' does not exist. It has been created.")
                            else:
                                # if set to false, we set the category to null
                                category = None
                                infos.append(f"Category '{imported_analytic['category'].strip()}' does not exist. Analytic will be created without category.")
                    else:
                        category = None
                        infos.append(f"Category key not found in JSON. Analytic will be created without category.")

                if not stop:
                    # fix out of band confidence
                    confidence = int(imported_analytic['confidence']) if "confidence" in imported_analytic else 1
                    if confidence < 1 or confidence > 4:
                        confidence = 1
                        infos.append(f"Confidence '{imported_analytic['confidence']}' is out of bounds. It has been set to 1.")
                    # fix out of band relevance
                    relevance = int(imported_analytic['relevance']) if "relevance" in imported_analytic else 1
                    if relevance < 1 or relevance > 4:
                        relevance = 1
                        infos.append(f"Relevance '{imported_analytic['relevance']}' is out of bounds. It has been set to 1.")

                    try:
                        # We try to save the analytic
                        analytic = Analytic(
                            name = imported_analytic['name'].strip(),
                            description = re_escape(imported_analytic['description']) if "description" in imported_analytic else "",
                            notes = re_escape(imported_analytic['notes']) if "notes" in imported_analytic else "",
                            status = REPO_SYNC_DEFAULT_STATUS,
                            confidence = confidence,
                            relevance = relevance,
                            category = category,
                            repo = repo,
                            connector = connector,
                            query = re_escape(imported_analytic['query']),
                            columns = re_escape(imported_analytic['columns']) if "columns" in imported_analytic else "",
                            emulation_validation = re_escape(imported_analytic['emulation_validation']) if "emulation_validation" in imported_analytic else "",
                            references = imported_analytic['references'] if "references" in imported_analytic else "",
                            run_daily = REPO_SYNC_DEFAULT_RUN_DAILY
                        )
                        
                        if mode == "sync":
                            # if mode is sync, we really save the analytic
                            analytic.save()
                        else:
                            # If mode is check, we just want to validate the analytic without saving it
                            analytic.full_clean()

                    except ValidationError as e:
                        errors.append(e.message_dict)
                        stop = True

                    if not stop:

                        # If the analytic is saved, we can now add the M2M fields

                        if mode == "sync":

                            if "target_os" in imported_analytic:
                                for os in imported_analytic['target_os']:
                                    try:
                                        target_os = get_object_or_404(TargetOs, name=os)
                                        analytic.target_os.add(target_os)
                                    except Exception as e:
                                        # We never create target OS. If missing, we just ignore target OS
                                        infos.append(f"Missing target OS: {str(e)}")
                            else:
                                infos.append(f"Missing target OS in JSON. Analytic created without target OS")

                            if "mitre_techniques" in imported_analytic:
                                for mitre_technique in imported_analytic['mitre_techniques']:
                                    try:
                                        mitre_technique = get_object_or_404(MitreTechnique, mitre_id=mitre_technique)
                                        analytic.mitre_techniques.add(mitre_technique)
                                    except Exception as e:
                                        # We never create MITRE techniques. If missing, we just ignore MITRE techniques
                                        infos.append(f"Missing MITRE Technique: {str(e)}")
                            else:
                                infos.append(f"Missing MITRE Techniques in JSON. Analytic created without MITRE Techniques")

                            if "threats" in imported_analytic:
                                for threat in imported_analytic['threats']:
                                    try:
                                        threat = get_object_or_404(ThreatName, name=threat)
                                        analytic.threats.add(threat)
                                    except Http404 as e:
                                        if REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST['threats'].lower() == 'true':
                                            threat = ThreatName(name=threat)
                                            threat.save()
                                            infos.append(f"Threat '{threat}' does not exist. It's been created.")
                                        else:
                                            infos.append(f"Threat '{threat}' does not exist. Analytic created without this threat.")
                            else:
                                infos.append(f"Missing threats in JSON. Analytic created without threats")

                            if "actors" in imported_analytic:
                                for actor in imported_analytic['actors']:
                                    try:
                                        actor = get_object_or_404(ThreatActor, name=actor)
                                        analytic.actors.add(actor)
                                    except Http404 as e:
                                        if REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST['actors'].lower() == 'true':
                                            actor = ThreatActor(name=actor)
                                            actor.save()
                                            infos.append(f"Threat actor '{actor}' does not exist. It's been created.")
                                        else:
                                            infos.append(f"Threat actor '{actor}' does not exist. Analytic created without this threat actor.")
                            else:
                                infos.append(f"Missing actors in JSON. Analytic created without actors.")

                            if "vulnerabilities" in imported_analytic:
                                for vulnerability in imported_analytic['vulnerabilities']:
                                    try:
                                        vulnerability = get_object_or_404(Vulnerability, name=vulnerability)
                                        analytic.vulnerabilities.add(vulnerability)
                                    except Http404 as e:
                                        if REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST['vulnerabilities'].lower() == 'true':
                                            vulnerability = Vulnerability(name=vulnerability)
                                            vulnerability.save()
                                            infos.append(f"Vulnerability '{vulnerability}' does not exist. It's been created.")
                                        else:
                                            infos.append(f"Vulnerability '{vulnerability}' does not exist. Analytic created without this vulnerability.")
                            else:
                                infos.append(f"Missing vulnerabilities in JSON. Analytic created without vulnerabilities.")

                        else: # mode check

                            with transaction.atomic():
                                analytic.save()  # Required to assign a PK before M2M can be added


                                if "target_os" in imported_analytic:
                                    for os in imported_analytic['target_os']:
                                        try:
                                            target_os = get_object_or_404(TargetOs, name=os)
                                            analytic.target_os.add(target_os)
                                        except Exception as e:
                                            # We never create target OS. If missing, we just ignore target OS
                                            infos.append(f"Missing target OS: {str(e)}")
                                else:
                                    infos.append(f"Missing target OS in JSON. Analytic created without target OS")

                                if "mitre_techniques" in imported_analytic:
                                    for mitre_technique in imported_analytic['mitre_techniques']:
                                        try:
                                            mitre_technique = get_object_or_404(MitreTechnique, mitre_id=mitre_technique)
                                            analytic.mitre_techniques.add(mitre_technique)
                                        except Exception as e:
                                            # We never create MITRE techniques. If missing, we just ignore MITRE techniques
                                            infos.append(f"Missing MITRE Technique: {str(e)}")
                                else:
                                    infos.append(f"Missing MITRE Techniques in JSON. Analytic created without MITRE Techniques")

                                if "threats" in imported_analytic:
                                    for threat in imported_analytic['threats']:
                                        try:
                                            threat = get_object_or_404(ThreatName, name=threat)
                                            analytic.threats.add(threat)
                                        except Http404 as e:
                                            if REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST['threats'].lower() == 'true':
                                                threat = ThreatName(name=threat)
                                                threat.save()
                                                infos.append(f"Threat '{threat}' does not exist. It's been created.")
                                            else:
                                                infos.append(f"Threat '{threat}' does not exist. Analytic created without this threat.")
                                else:
                                    infos.append(f"Missing threats in JSON. Analytic created without threats")

                                if "actors" in imported_analytic:
                                    for actor in imported_analytic['actors']:
                                        try:
                                            actor = get_object_or_404(ThreatActor, name=actor)
                                            analytic.actors.add(actor)
                                        except Http404 as e:
                                            if REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST['actors'].lower() == 'true':
                                                actor = ThreatActor(name=actor)
                                                actor.save()
                                                infos.append(f"Threat actor '{actor}' does not exist. It's been created.")
                                            else:
                                                infos.append(f"Threat actor '{actor}' does not exist. Analytic created without this threat actor.")
                                else:
                                    infos.append(f"Missing actors in JSON. Analytic created without actors.")

                                if "vulnerabilities" in imported_analytic:
                                    for vulnerability in imported_analytic['vulnerabilities']:
                                        try:
                                            vulnerability = get_object_or_404(Vulnerability, name=vulnerability)
                                            analytic.vulnerabilities.add(vulnerability)
                                        except Http404 as e:
                                            if REPO_SYNC_CREATE_FIELD_IF_NOT_EXIST['vulnerabilities'].lower() == 'true':
                                                vulnerability = Vulnerability(name=vulnerability)
                                                vulnerability.save()
                                                infos.append(f"Vulnerability '{vulnerability}' does not exist. It's been created.")
                                            else:
                                                infos.append(f"Vulnerability '{vulnerability}' does not exist. Analytic created without this vulnerability.")
                                else:
                                    infos.append(f"Missing vulnerabilities in JSON. Analytic created without vulnerabilities.")


                                # This silently rolls back at the end
                                transaction.set_rollback(True)

                if errors:
                    nb_analytics_errors += 1
                else:
                    nb_analytics_valid += 1
                        
                analytics.append({
                    "name": analytic_name,
                    "url": content.get('html_url'),
                    "errors": errors,
                    "infos": infos,
                })
    
    if mode == "sync":
        # Update the sync date
        repo.last_sync_date = datetime.now()
        repo.save()
    else:
        # Update the number of analytics in the repo
        repo.nb_analytics = nb_analytics
        repo.nb_analytics_valid = nb_analytics_valid
        repo.nb_analytics_errors = nb_analytics_errors
        repo.last_check_date = datetime.now()
        repo.save()


    context = {
        "analytics": analytics,
        "repo": repo,
        "nb_analytics": nb_analytics,
        "nb_analytics_errors": nb_analytics_errors,
        "nb_analytics_valid": nb_analytics_valid,
    }
    return render(request, 'sync_repo_report.html', context)


@login_required
def delete_repo(request, repo_id):
    repo = get_object_or_404(Repo, pk=repo_id)
    repo.delete()
    return HttpResponseRedirect(reverse('list_repos'))

@login_required
def add_repo(request):
    if request.method == "POST":
        form = RepoForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('list_repos'))
    else:
        form = RepoForm()
    return render(request, 'add_repo.html', {'form': form})

@login_required
def edit_repo(request, repo_id):
    repo = get_object_or_404(Repo, pk=repo_id)
    form = RepoForm(instance=repo)
    
    if request.method == "POST":
        form = RepoForm(
            request.POST,
            instance=repo
        )
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('list_repos'))
    
    context = {
        'form': form,
        'repo': repo,
    }
    return render(request, 'edit_repo.html', context)
