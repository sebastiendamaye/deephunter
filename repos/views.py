from django.shortcuts import render, get_object_or_404, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.conf import settings
from qm.models import TasksStatus
from repos.models import Repo
from .forms import RepoForm
from repos.tasks import import_repo_task
import requests
from urllib.parse import unquote
import base64
from notifications.utils import add_debug_notification, add_error_notification, add_success_notification, add_info_notification
from celery import current_app
from .utils import nb_analytics_imported, is_imported

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

@login_required
def list_repos(request):
    repos = []
    for repo in Repo.objects.all():
        repos.append({
            "id": repo.id,
            "name": repo.name,
            "url": repo.url,
        })
    context = {"repos": repos}
    return render(request, "list_repos.html", context)

def get_repo_import_info(request, repo_id):
    repo = get_object_or_404(Repo, pk=repo_id)
    context = {
            "repo_id": repo.id,
            "nb_analytics": repo.repoanalytic_set.count(),
            "nb_analytics_imported": nb_analytics_imported(repo),
            "nb_analytics_valid": repo.repoanalytic_set.filter(is_valid=True).count(),
            "nb_analytics_errors": repo.repoanalytic_set.filter(is_valid=False).count(),
            "last_check_date": repo.last_check_date,
            "last_import_date": repo.last_import_date,
    }
    return render(request, "partials/repo_import_info.html", context)

@login_required
def import_repo_select_analytics(request, repo_id):
    repo = get_object_or_404(Repo, pk=repo_id)
    if "github.com" in repo.url:
        contents = all_connectors.get('github').get_github_contents(repo.url)
    elif "bitbucket.org" in repo.url:
        contents = all_connectors.get('bitbucket').get_bitbucket_contents(repo.url)
    context = {
        "repo": repo,
        "contents": contents,
    }
    return render(request, 'import_repo_select_analytics.html', context)

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

@login_required
def report(request, repo_id):
    repo = get_object_or_404(Repo, pk=repo_id)
    
    analytics = []
    for a in repo.repoanalytic_set.all():
        analytics.append(
            {
                "name": a.name,
                "url": a.url,
                "report": a.report,
                "is_valid": a.is_valid,
                "is_imported": is_imported(a.name, repo),
            }
        )    
    
    context = {
        'repo': repo,
        'nb_analytics': repo.repoanalytic_set.count(),
        'nb_analytics_valid': repo.repoanalytic_set.filter(is_valid=True).count(),
        'nb_analytics_errors': repo.repoanalytic_set.filter(is_valid=False).count(),
        'nb_analytics_imported': nb_analytics_imported(repo),
        'analytics': analytics,
    }
    return render(request, 'report.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def import_repo(request, repo_id, mode):

    selected_analytics = None

    if request.method == "POST":
        selected_analytics = request.POST.getlist('analytics')

    # start the celery task
    taskid = import_repo_task.delay(repo_id, mode, selected_analytics)

    # Create task in TasksStatus object
    celery_status = TasksStatus(
        taskname = f"import_repo_{repo_id}",
        taskid = taskid
    )
    celery_status.save()

    if mode == 'check':
        return HttpResponse('running...')
    else:
        return HttpResponseRedirect(reverse('list_repos'))

@login_required
@permission_required("repo.change_repo")
def progress_import_repo(request, repo_id):
    try:
        repo = get_object_or_404(Repo, pk=repo_id)
        celery_status = get_object_or_404(TasksStatus, taskname=f"import_repo_{repo.id}")
        button = f'<span><b>Task progress:</b> {round(celery_status.progress)}%'
        button += f' | <button hx-get="/repos/cancel-import-repo/{celery_status.taskid}/" class="buttonred">CANCEL</button></span>'
        return HttpResponse(button)
    except:
        return HttpResponse(f'<button hx-get="/repos/importrepo/{repo_id}/check/" class="button">check</button>'
            + f'&nbsp;<a href="/repos/importreposelectanalytics/{repo_id}/" class="button">Import</a>')

@login_required
@permission_required("repo.change_repo")
def cancel_import_repo(request, taskid):
    try:
        # without signal='SIGKILL', the task is not cancelled immediately
        current_app.control.revoke(taskid, terminate=True, signal='SIGKILL')
        # delete task in DB
        celery_status = get_object_or_404(TasksStatus, taskid=taskid)
        celery_status.delete()
        add_info_notification(f'User aborted repo import: {celery_status.taskname}')
        return HttpResponse('stopping...')
    except Exception as e:
        add_error_notification(f'Cancel import repo: Error terminating Celery Task: {e}')
        return HttpResponse(f'Error terminating Celery Task: {e}')
