from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy import stats
from math import isnan
from .models import (Country, Analytic, Snapshot, Campaign, TargetOs, Vulnerability, ThreatActor,
    ThreatName, MitreTactic, MitreTechnique, Endpoint, Tag, TasksStatus, Category, Review, SavedSearch, Repo)
from connectors.models import Connector
from .tasks import regenerate_stats, regenerate_campaign
import ipaddress
from connectors.utils import is_connector_enabled, is_connector_for_analytics, get_connector_conf
from celery import current_app
from qm.utils import get_campaign_date, get_available_statuses
from urllib.parse import urlencode, quote
from .forms import ReviewForm, EditAnalyticDescriptionForm, EditAnalyticNotesForm, EditAnalyticQueryForm, SavedSearchForm
from notifications.utils import add_error_notification

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module


PROXY = settings.PROXY
STATIC_PATH = settings.STATIC_ROOT
BASE_DIR = settings.BASE_DIR
UPDATE_ON = settings.UPDATE_ON
DB_DATA_RETENTION = settings.DB_DATA_RETENTION
GITHUB_LATEST_RELEASE_URL = settings.GITHUB_LATEST_RELEASE_URL
GITHUB_COMMIT_URL = settings.GITHUB_COMMIT_URL
CAMPAIGN_MAX_HOSTS_THRESHOLD = settings.CAMPAIGN_MAX_HOSTS_THRESHOLD
ON_MAXHOSTS_REACHED = settings.ON_MAXHOSTS_REACHED
ANALYTICS_PER_PAGE = settings.ANALYTICS_PER_PAGE
DAYS_BEFORE_REVIEW = settings.DAYS_BEFORE_REVIEW

@login_required
def dashboards(request):
    context = {}
    return render(request, 'dashboards.html', context)

@login_required
def list_analytics(request):

    analytics = Analytic.objects.all().order_by('id')
    
    posted_search = ''
    posted_filters = {}
    
    if request.GET:
        
        if 'search' in request.GET:
            analytics = analytics.filter(
                Q(name__icontains=request.GET['search'])
                | Q(description__icontains=request.GET['search'])
                | Q(notes__icontains=request.GET['search'])
            )
            posted_search = request.GET['search']
            
        if 'connectors' in request.GET:
            analytics = analytics.filter(connector__pk__in=request.GET.getlist('connectors'))
            posted_filters['connectors'] = request.GET.getlist('connectors')

        if 'repos' in request.GET:
            analytics = analytics.filter(repo__pk__in=request.GET.getlist('repos'))
            posted_filters['repos'] = request.GET.getlist('repos')

        if 'categories' in request.GET:
            analytics = analytics.filter(category__pk__in=request.GET.getlist('categories'))
            posted_filters['categories'] = request.GET.getlist('categories')

        if 'target_os' in request.GET:
            analytics = analytics.filter(target_os__pk__in=request.GET.getlist('target_os'))
            posted_filters['target_os'] = request.GET.getlist('target_os')
        
        if 'vulnerabilities' in request.GET:
            analytics = analytics.filter(vulnerabilities__pk__in=request.GET.getlist('vulnerabilities'))
            posted_filters['vulnerabilities'] = request.GET.getlist('vulnerabilities')
        
        if 'tags' in request.GET:
            analytics = analytics.filter(tags__pk__in=request.GET.getlist('tags'))
            posted_filters['tags'] = request.GET.getlist('tags')
        
        if 'actors' in request.GET:
            analytics = analytics.filter(actors__pk__in=request.GET.getlist('actors'))
            posted_filters['actors'] = request.GET.getlist('actors')
        
        if 'source_countries' in request.GET:
            # List of all APT associated to the selected source countries
            apt = []
            for countryid in request.GET.getlist('source_countries'):
                country = get_object_or_404(Country, pk=countryid)
                for i in ThreatActor.objects.filter(source_country=country):
                    apt.append(i.id)
            analytics = analytics.filter(actors__pk__in=apt)
            posted_filters['source_countries'] = request.GET.getlist('source_countries')
        
        if 'threats' in request.GET:
            analytics = analytics.filter(threats__pk__in=request.GET.getlist('threats'))
            posted_filters['threats'] = request.GET.getlist('threats')
        
        if 'mitre_techniques' in request.GET:
            analytics = analytics.filter(
                Q(mitre_techniques__pk__in=request.GET.getlist('mitre_techniques'))
                | Q(mitre_techniques__mitre_technique__pk__in=request.GET.getlist('mitre_techniques'))
            )
            posted_filters['mitre_techniques'] = request.GET.getlist('mitre_techniques')
        
        if 'mitre_tactics' in request.GET:
            analytics = analytics.filter(mitre_techniques__mitre_tactic__pk__in=request.GET.getlist('mitre_tactics'))
            posted_filters['mitre_tactics'] = request.GET.getlist('mitre_tactics')
        
        if 'confidence' in request.GET:
            analytics = analytics.filter(confidence__in=request.GET.getlist('confidence'))
            posted_filters['confidence'] = request.GET.getlist('confidence')
        
        if 'relevance' in request.GET:
            analytics = analytics.filter(relevance__in=request.GET.getlist('relevance'))
            posted_filters['relevance'] = request.GET.getlist('relevance')

        if 'statuses' in request.GET:
            analytics = analytics.filter(status__in=request.GET.getlist('statuses'))
            posted_filters['statuses'] = request.GET.getlist('statuses')

        if 'run_daily' in request.GET:
            if request.GET['run_daily'] == '1':
                analytics = analytics.filter(run_daily=True)
                posted_filters['run_daily'] = 1
            else:
                analytics = analytics.filter(run_daily=False)
                posted_filters['run_daily'] = 0
            
        if 'create_rule' in request.GET:
            if request.GET['create_rule'] == '1':
                analytics = analytics.filter(create_rule=True)
                posted_filters['create_rule'] = 1
            else:
                analytics = analytics.filter(create_rule=False)
                posted_filters['create_rule'] = 0

        if 'dynamic_query' in request.GET:
            if request.GET['dynamic_query'] == '1':
                analytics = analytics.filter(dynamic_query=True)
                posted_filters['dynamic_query'] = 1
            else:
                analytics = analytics.filter(dynamic_query=False)
                posted_filters['dynamic_query'] = 0

        if 'hits' in request.GET:
            # Get yesterday's date
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_date = yesterday.date()  # Get the date part

            if request.GET['hits'] == '1':
                # Filter queries where related Snapshot has hits_count > 0 and date is yesterday
                analytics = analytics.filter(
                    snapshot__hits_count__gt=0,
                    snapshot__date=yesterday_date
                ).distinct()
                posted_filters['hits'] = 1
            else:
                # Filter analytics where related Snapshot has hits_count = 0 and date is yesterday
                analytics = analytics.filter(
                    snapshot__hits_count=0,
                    snapshot__date=yesterday_date
                ).distinct()
                posted_filters['hits'] = 0

        if 'alreadyseen' in request.GET:
            if request.GET['alreadyseen'] == '1':
                analytics = analytics.filter(last_time_seen__isnull=False)
                posted_filters['alreadyseen'] = 1
            else:
                analytics = analytics.filter(last_time_seen__isnull=True)
                posted_filters['alreadyseen'] = 0

        if 'maxhosts' in request.GET:
            if request.GET['maxhosts'] == '1':
                analytics = analytics.filter(maxhosts_count__gt=0)
                posted_filters['maxhosts'] = 1
            else:
                analytics = analytics.filter(maxhosts_count=0)
                posted_filters['maxhosts'] = 0

        if 'queryerror' in request.GET:
            if request.GET['queryerror'] == '1':
                analytics = analytics.filter(query_error=True)
                posted_filters['queryerror'] = 1
            else:
                analytics = analytics.filter(query_error=False)
                posted_filters['queryerror'] = 0

        if 'created_by' in request.GET:
            analytics = analytics.filter(created_by__pk__in=request.GET.getlist('created_by'))
            posted_filters['created_by'] = request.GET.getlist('created_by')

    # Exclude analytics that are archived
    analytics = analytics.exclude(status='ARCH').distinct()

    for analytic in analytics:
        snapshot = Snapshot.objects.filter(analytic=analytic, date=datetime.today()-timedelta(days=1)).order_by('date')
        if len(snapshot) > 0:
            snapshot = snapshot[0]
            analytic.hits_endpoints = snapshot.hits_endpoints
            analytic.hits_count = snapshot.hits_count
            analytic.anomaly_alert_count = snapshot.anomaly_alert_count
            analytic.anomaly_alert_endpoints = snapshot.anomaly_alert_endpoints
        else:
            analytic.hits_endpoints = 0
            analytic.hits_count = 0
        
        # Sparkline: show sparkline only for last 20 days event count
        snapshots = Snapshot.objects.filter(analytic=analytic, date__gt=datetime.today()-timedelta(days=20))
        analytic.sparkline = [snapshot.hits_endpoints for snapshot in snapshots]
        
    # Paginate the analytics list
    analytics_count = analytics.count()
    paginator = Paginator(analytics, ANALYTICS_PER_PAGE)
    page_number = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page_number)
    # Save filters to query string for pagination
    querydict = request.GET.copy()
    if 'page' in querydict:
        del querydict['page']
    query_string = querydict.urlencode()

    # for "save search" feature
    filtered_querydict = request.GET.copy()
    if 'page' in filtered_querydict:
        del filtered_querydict['page']
    if 'csrfmiddlewaretoken' in filtered_querydict:
        del filtered_querydict['csrfmiddlewaretoken']
    if 'search' in request.GET:
        if request.GET['search'].strip() == '':
            del filtered_querydict['search']
    if filtered_querydict:
        filtered_query_string = quote(filtered_querydict.urlencode(), safe='')
    else:
        filtered_query_string = ''

    context = {
        'analytics': page_obj,
        'query_string': query_string,
        'filtered_query_string': filtered_query_string,
        'analytics_count': analytics_count,
        'connectors': Connector.objects.filter(domain="analytics"),
        'repos': Repo.objects.all(),
        'target_os': TargetOs.objects.all(),
        'vulnerabilities': Vulnerability.objects.all(),
        'tags': Tag.objects.all(),
        'threat_actors': ThreatActor.objects.all(),
        'source_countries': Country.objects.all(),
        'threat_names': ThreatName.objects.all(),
        'mitre_tactics': MitreTactic.objects.all(),
        'mitre_techniques': MitreTechnique.objects.all(),
        'categories': Category.objects.all(),
        'statuses': [{'name': name, 'description': description} for name,description in Analytic.STATUS_CHOICES if name != 'ARCH'],
        'created_by': User.objects.filter(id__in=Analytic.objects.exclude(created_by__isnull=True).values('created_by').distinct()),
        'posted_search': posted_search,
        'posted_filters': posted_filters,
    }
    return render(request, 'list_analytics.html', context)
    
@login_required
def trend(request, analytic_id, tab=0):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    # show graph for last 90 days only
    snapshots = Snapshot.objects.filter(analytic=analytic, date__gt=datetime.today()-timedelta(days=90)).order_by('date')
    
    stats_vals = []
    date = [snapshot.date for snapshot in snapshots]
    runtime = [snapshot.runtime for snapshot in snapshots]
    a_count = np.array([snapshot.hits_count for snapshot in snapshots])
    z_count = stats.zscore(a_count)
    a_endpoints = np.array([snapshot.hits_endpoints for snapshot in snapshots])
    z_endpoints = stats.zscore(a_endpoints)
    a_anomaly_alert_count = np.array([snapshot.anomaly_alert_count for snapshot in snapshots])
    a_anomaly_alert_endpoints = np.array([snapshot.anomaly_alert_endpoints for snapshot in snapshots])

    for i,v in enumerate(a_count):
        stats_vals.append( {
            'date': date[i],
            'runtime': runtime[i],
            'hits_count': a_count[i],
            'zscore_count': z_count[i],
            'hits_endpoints': a_endpoints[i],
            'zscore_endpoints': z_endpoints[i],
            'anomaly_alert_count': a_anomaly_alert_count[i],
            'anomaly_alert_endpoints': a_anomaly_alert_endpoints[i]
            } )

    endpoints = Endpoint.objects.filter(snapshot__analytic=analytic).values('hostname').distinct()

    context = {
        'analytic': analytic,
        'stats': stats_vals,
        'distinct_endpoints': endpoints.count(),
        'endpoints': endpoints,
        'tab': tab,
        }
    return render(request, 'trend.html', context)

@login_required
def analyticdetail(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)    
    
    # Populate the list of endpoints (top 10) that matched the analytic for the last campaign
    try:
        snapshots = Snapshot.objects.filter(analytic=analytic, date=datetime.today()-timedelta(days=1))
        endpoints = []
        for snapshot in snapshots:
            for e in Endpoint.objects.filter(snapshot=snapshot):
                endpoints.append(e.hostname)
        # remove duplicated values (due to endpoints appearing in several snapshots)
        endpoints = list(set(endpoints))[:10]
    except:
        endpoints = []

    # get celery status for the selected analytic
    try:
        celery_status = get_object_or_404(TasksStatus, taskname=analytic.name)
        progress = round(celery_status.progress)
    except:
        progress = 999
            
    context = {
        'analytic': analytic,
        'endpoints': endpoints,
        'progress': progress
        }
    return render(request, 'analytic_detail.html', context)

@login_required
def timeline(request):

    hostname = ''

    if request.GET:
        hostname = request.GET['hostname'].strip()
    
    context = {
        'hostname': hostname,
        }
    return render(request, 'timeline.html', context)

@login_required
def tl_timeline(request, hostname):

    groups = []
    items = []
    items2 = []
    gid = 0 # group id
    iid = 0 # item id
    storylineid_json = {}
    connectors_json = {}

    apps = ''

    endpoints = Endpoint.objects.filter(hostname=hostname).order_by('snapshot__date')
    for e in endpoints:
        # search if group already exists
        g = next((group for group in groups if group['content'] == f'{e.snapshot.analytic.name} ({e.snapshot.analytic.connector.name})'), None)
        # if group does not exist yet, create it
        if g:
            g = g['id']
        else:
            groups.append({'id':gid, 'analyticid':e.snapshot.analytic.id, 'content':f'{e.snapshot.analytic.name} ({e.snapshot.analytic.connector.name})'})
            g = gid
            gid += 1
            
        # populate items and refer to relevant group
        items.append({
            'id': iid,
            'group': g,
            'start': e.snapshot.date,
            'end': e.snapshot.date+timedelta(days=1),
            'description': 'Signature: {}'.format(e.snapshot.analytic.name),
            'connector': 'Connector: {}'.format(e.snapshot.analytic.connector.name),
            'storylineid': 'StorylineID: {}'.format(e.storylineid.replace('#', ', '))
            })
        storylineid_json[iid] = e.storylineid.split('#')
        connectors_json[iid] = e.snapshot.analytic.connector.name
        iid += 1
    

    # Populate threats (group ID >= 1000 for easy identification in template)
    gid = 1000
    sincedate = (datetime.today()-timedelta(days=DB_DATA_RETENTION)).isoformat()

    # Recursively call the get_threats function in each connector to build a consolidated list of threats
    for connector in all_connectors.values():

        connector_name = connector.__name__.split('.')[1]

        # we only call get_threats() if the connector is enabled and has this method
        if is_connector_enabled(connector_name) and is_connector_for_analytics(connector_name) and hasattr(connector, 'get_threats'):
            # If the connector has a get_threats method, call it
            #try:
            threats = connector.get_threats(hostname, sincedate)

            if threats:
                groups.append({'id':gid, 'content':f'Threats ({connector_name})'})
                for threat in threats:
                    detectedat = threat['threatInfo']['identifiedAt']
                    items.append({
                        'id': iid,
                        'group': gid,
                        'start': datetime.strptime(detectedat, '%Y-%m-%dT%H:%M:%S.%fZ'),
                        'end': datetime.strptime(detectedat, '%Y-%m-%dT%H:%M:%S.%fZ')+timedelta(days=1),
                        'description': '{} [{}] [{}]'.format(
                            threat['threatInfo']['threatName'],
                            threat['threatInfo']['analystVerdict'],
                            threat['threatInfo']['confidenceLevel']
                            ),
                        'storylineid': 'StorylineID: {}'.format(threat['threatInfo']['storyline']),
                        'connector': f'Connector: {connector_name}'
                        })
                    storylineid_json[iid] = [threat['threatInfo']['storyline']]
                    connectors_json[iid] = connector_name
                    iid += 1
            #except Exception as e:
            #    print(f"Error getting threats for {hostname}")
        
            # We increment the group ID for each connector to ensure unique group IDs
            gid += 1

    ###
    # The below content is only available if SentinelOne connector is enabled
    ###
    if is_connector_enabled('sentinelone'):

        # Get machine details from SentinelOne            
        machinedetails = all_connectors.get('sentinelone').get_machine_details(hostname)
        if machinedetails:
            agent_id = machinedetails['id']

            if agent_id:
            
                # Populate applications (group ID = 500 for easy identification in template)
                gid = 500
                groups.append({'id':gid, 'content':'Apps install (sentinelone)'})
                
                createdat = (datetime.today()-timedelta(days=DB_DATA_RETENTION))
                apps = all_connectors.get('sentinelone').get_applications(agent_id)
                
                for app in apps:
                    if app['installedDate']:
                        if datetime.strptime(app['installedDate'][:10], '%Y-%m-%d') >= createdat:
                            items.append({
                                'id': iid,
                                'group': gid,
                                'start':  datetime.strptime(app['installedDate'][:10], '%Y-%m-%d'),
                                'end': datetime.strptime(app['installedDate'][:10], '%Y-%m-%d')+timedelta(days=1),
                                'description': '{} ({})'.format(app['name'].strip(), app['publisher'].strip())
                                })
                            iid += 1
                
                

    # Visualization #2 (graph)
    items2 = Endpoint.objects.filter(hostname=hostname) \
        .values('snapshot__date') \
        .annotate(cumulative_score=Sum('snapshot__analytic__weighted_relevance')) \
        .order_by('snapshot__date')


    context = {
        'hostname': hostname,
        'apps': apps,
        'groups': groups,
        'items': items,
        'items2': items2,
        'mindate': datetime.today()-timedelta(days=DB_DATA_RETENTION+1),
        'maxdate': datetime.today()+timedelta(days=1),
        'storylineid_json': storylineid_json,
        'connectors_json': connectors_json,
        }
    return render(request, 'tl_timeline.html', context)


@login_required
def tl_host(request, hostname):

    machinedetails = {}
    user_name = ''
    job_title = ''
    business_unit = ''
    location = ''

    if is_connector_enabled('sentinelone'):

        # Get machine details from SentinelOne            
        machinedetails = all_connectors.get('sentinelone').get_machine_details(hostname)
        if machinedetails:
            agent_id = machinedetails['id']

            if agent_id:
                # Get username
                username = all_connectors.get('sentinelone').get_last_logged_in_user(agent_id)
                entry = all_connectors.get('activedirectory').ldap_search(username)
                if entry:
                    user_name = entry.displayName
                    job_title = entry.title
                    business_unit = entry.division
                    location = "{}, {}".format(entry.physicalDeliveryOfficeName, entry.co)
    
    context = {
        'machinedetails': machinedetails,
        'user_name': user_name,
        'job_title': job_title,
        'business_unit': business_unit,
        'location': location,
        }
    return render(request, 'tl_host.html', context)


@login_required
def tl_ad(request, hostname):

    machinedetails = {}
    if is_connector_enabled('sentinelone'):

        # Get machine details from SentinelOne            
        machinedetails = all_connectors.get('sentinelone').get_machine_details(hostname)
    
    context = {
        'machinedetails': machinedetails,
        }
    return render(request, 'tl_ad.html', context)

@login_required
def tl_apps(request, hostname):

    if is_connector_enabled('sentinelone'):
        # Get machine details from SentinelOne            
        machinedetails = all_connectors.get('sentinelone').get_machine_details(hostname)
        if machinedetails:
            agent_id = machinedetails['id']
            if agent_id:            
                apps = all_connectors.get('sentinelone').get_applications(agent_id)

    context = {
        'apps': apps,
        }
    return render(request, 'tl_apps.html', context)

@login_required
def events(request, analytic_id, eventdate=None, endpointname=None):
    """
    Redirect to the analytic link in the connector's data lake.
    """
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    return HttpResponseRedirect(all_connectors.get(analytic.connector.name).get_redirect_analytic_link(analytic, eventdate, endpointname))

@login_required
def threats(request, connector, endpointname, date):
    """
    Redirect to the threats link in the connector's data lake.
    """
    return HttpResponseRedirect(all_connectors.get(connector).get_redirect_threats_link(endpointname, date))

@login_required
def storyline(request, storylineids, eventdate):
    """
    Redirect to Singularity DataLake in S1 with results related to the queried storyline ID(s).
    Only relevant for SentinelOne connector.
    """
    return HttpResponseRedirect(all_connectors.get('sentinelone').get_redirect_storyline_link(storylineids, eventdate))

@login_required
@permission_required("qm.delete_campaign")
def regen(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
        
    # start the celery task (defined in qm/tasks.py)
    taskid = regenerate_stats.delay(analytic_id)

    # Create task in TasksStatus object
    celery_status = TasksStatus(
        taskname=analytic.name,
        taskid = taskid
    )
    celery_status.save()

    return HttpResponse('running...')

@login_required
@permission_required("qm.delete_campaign")
def cancelregen(request, taskid):
    try:
        # without signal='SIGKILL', the task is not cancelled immediately
        current_app.control.revoke(taskid, terminate=True, signal='SIGKILL')
        # delete task in DB
        celery_status = get_object_or_404(TasksStatus, taskid=taskid)
        celery_status.delete()
        return HttpResponse('stopping...')
    except Exception as e:
        add_error_notification(f'Cancel stats regeneration: Error terminating Celery Task: {e}')
        return HttpResponse(f'Error terminating Celery Task: {e}')

@login_required
@permission_required("qm.delete_campaign")
def progress(request, analytic_id):
    try:
        analytic = get_object_or_404(Analytic, pk=analytic_id)
        celery_status = get_object_or_404(TasksStatus, taskname=analytic.name)
        button = f'<span><b>Task progress:</b> {round(celery_status.progress)}%'
        button += f' | <button hx-get="/cancelregen/{celery_status.taskid}/" class="buttonred">CANCEL</button></span>'
        return HttpResponse(button)
    except:
        return HttpResponse('<button hx-get="/{}/regen/" class="buttonred">Regenerate stats</button>'.format(analytic_id))

@login_required
@permission_required("qm.delete_campaign")
def deletestats(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    Snapshot.objects.filter(analytic=analytic).delete()
    return HttpResponse('Stats deleted')

@login_required
def netview(request):
    debug = ''    
    ips = []
    if request.GET:
        if 'hostname' in request.GET:
            hostname = request.GET['hostname'].strip()
        else:
            hostname = ''
        
        if 'storylineid' in request.GET:
            storylineid = request.GET['storylineid'].strip()
        else:
            storylineid = ''
            
        if 'timerange' in request.GET:
            timerange = int(request.GET['timerange'])
        else:
            timerange = 24
        
        if hostname == '' and storylineid == '':
            debug = 'Missing Endpoint and/or Storyline ID'

        else:

            r = all_connectors.get('sentinelone').get_network_connections(storylineid, hostname, timerange)

            if len(r['data']) != 0:
                data = r['data']
                for ip in data:
                    
                    if ip[0]:
                        # if private ip, don't scan with VT
                        if ipaddress.ip_address(ip[0]).is_private:
                            iptype = 'PRIV'
                            vt = ''
                        else:
                            iptype = 'PUBL'
                            vt = {}
                            response = all_connectors.get('virustotal').check_ip(ip[0])
                            try:
                                vt['malicious'] = response['attributes']['last_analysis_stats']['malicious']
                                vt['suspicious'] = response['attributes']['last_analysis_stats']['suspicious']
                                vt['whois'] = response['attributes']['whois']
                            except KeyError:
                                vt['malicious'] = 0
                                vt['suspicious'] = 0
                                vt['whois'] = ''
                                debug = 'No VT data for IP: {}'.format(ip[0])
                        
                        ips.append({
                            'dstip': ip[0],
                            'iptype': iptype,
                            'dstports': ip[2],
                            'freq': int(ip[3]),
                            'vt': vt
                            })
            
       
    else:
        hostname = ''
        storylineid = ''
        timerange = ''
    
    context = {
        'hostname': hostname,
        'storylineid': storylineid,
        'timerange': timerange,
        'ips': ips,
        'debug': debug
        }
    return render(request, 'netview.html', context)

@login_required
def about(request):    
    # local version
    with open(f'{STATIC_PATH}/VERSION', 'r') as f:
        version = f.readline().strip()
    # commit version
    with open(f'{STATIC_PATH}/commit_id.txt', 'r') as f:
        version_commit = f.readline().strip()
    # local version MITRE
    with open(f'{STATIC_PATH}/VERSION_MITRE', 'r') as f:
        version_mitre = f.readline().strip()
    
    context = {
        'version': version,
        'version_commit': version_commit,
        'version_mitre': version_mitre,
        }
    return render(request, 'about.html', context)

@login_required
def managecampaigns(request):
    campaigns = Campaign.objects.filter(name__startswith='daily_cron_').order_by('-name')
    context = {'campaigns': campaigns}
    return render(request, 'managecampaigns.html', context)

@login_required
@permission_required("qm.delete_campaign")
def regencampaign(request, campaign_name):
    campaign = get_object_or_404(Campaign, name=campaign_name)
    campaign_name = campaign.name
    campaign_date = get_campaign_date(campaign)
    # Delete campaign and all related snapshots/endpoints
    campaign.delete()
    
    # start the celery task (defined in qm/tasks.py)
    taskid = regenerate_campaign.delay(campaigndate=campaign_date)

    # Create task in TasksStatus object
    celery_status = TasksStatus(
        taskname=campaign_name,
        taskid=taskid
    )
    celery_status.save()

    return HttpResponse('running...')

@login_required
def regencampaignstatus(request, campaign_name):
    try:
        celery_status = get_object_or_404(TasksStatus, taskname=campaign_name)
        button = f'<span><b>Task progress:</b> {round(celery_status.progress)}%'
        # cancel task is only possible if task started from celery (not if campaign is running from cron)
        if celery_status.taskid:
            button += f' | <button hx-get="/cancelregen/{celery_status.taskid}/" class="buttonred">CANCEL</button>'
        button += '</span>'
        return HttpResponse(button)
    except:
        return HttpResponse(f'<button hx-get="/regencampaign/{campaign_name}/" class="buttonred">Regenerate</button>')

@login_required
def saved_searches(request):
    """
    Loads the saved searches page.
    """
    context = {}
    return render(request, 'saved_searches.html', context)

@login_required
def saved_searches_table(request):
    """
    Display saved searches for the current user.
    """
    only_show_user_saved_searches = request.GET.get('only_show_user_saved_searches', 'off') == 'on'  # Get checkbox value
    if only_show_user_saved_searches:
        saved_searches = SavedSearch.objects.filter(created_by=request.user).order_by('name')
    else:
        saved_searches = SavedSearch.objects.filter(Q(created_by=request.user) | Q(is_public=True)).order_by('name')
    context = {'saved_searches': saved_searches}
    return render(request, 'partials/saved_searches_table.html', context)

@login_required
def saved_search_form(request, search_id=None):
    if search_id:
        saved_search = get_object_or_404(SavedSearch, pk=search_id)
        # Only allow update if owned by the user or (public and unlocked)
        if not (saved_search.created_by == request.user or (saved_search.is_public and not saved_search.is_locked)):
            return HttpResponseForbidden("You do not have permission to update this saved search.")
        initial = {}
    else:
        saved_search = None
        # Get the initial search value from GET parameters
        initial = {}
        if 'search' in request.GET:
            initial['search'] = request.GET['search']

    if request.method == "POST":
        form = SavedSearchForm(request.POST, instance=saved_search)
        if form.is_valid():
            obj = form.save(commit=False)
            if not saved_search:
                obj.created_by = request.user

            obj.save()
            return HttpResponseRedirect(reverse('saved_searches'))
    else:
        form = SavedSearchForm(instance=saved_search, initial=initial)
    
    context = {
        "form": form,
        "saved_search": saved_search
    }
    return render(request, "saved_search_form.html", context)

@login_required
def delete_saved_search(request, search_id):
    saved_search = get_object_or_404(SavedSearch, pk=search_id)
    # Only allow delete if owned by the user or (public and unlocked)
    if (saved_search.created_by == request.user or (saved_search.is_public and not saved_search.is_locked)):
        saved_search.delete()
        return HttpResponseRedirect(reverse('saved_searches'))
    else:
        return HttpResponseForbidden("You do not have permission to delete this saved search.")

@login_required
def db_totalnumberanalytics(request):
    analytics = Analytic.objects.exclude(status='ARCH')    
    
    code = f"""<h3>Total number of analytics</h3>
        <p class="num"><a href="/qm/listanalytics/">{analytics.count()}</a></p>
        """
    return HttpResponse(code)

@login_required
def db_analyticsrunintodaycampaign(request):
    campaign = get_object_or_404(Campaign, name='daily_cron_{}'.format(datetime.today().strftime('%Y-%m-%d')))
    
    code = f"""<h3>Analytics run in today's campaign</h3>
        <p class="num"><a href="/qm/listanalytics/?run_daily=1">{campaign.nb_queries}</p>
        """
    return HttpResponse(code)

@login_required
def db_analyticsmatchingintodaycampaign(request):
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_date = yesterday.date()  # Get the date part

    analytics = Analytic.objects.filter(
        snapshot__hits_count__gt=0,
        snapshot__date=yesterday_date
    ).distinct()
    
    code = f"""<h3>Analytics triggered in last campaign</h3>
        <p class="num"><a href="/qm/listanalytics/?hits=1">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
def db_highestweightedscoretoday(request):

    campaign = get_object_or_404(Campaign, name='daily_cron_{}'.format(datetime.today().strftime('%Y-%m-%d')))

    qs = Endpoint.objects.filter(
        snapshot__campaign=campaign
    ).values('hostname').annotate(
        total_weighted_score=Sum(F('snapshot__analytic__weighted_relevance'))
    ).order_by('-total_weighted_score')

    # Get the highest score
    highestweightedscore = qs.first()
    
    code = f"""<h3>Highest weighted score today</h3>
        <p class="num"><a href="/reports/endpoints">{highestweightedscore['total_weighted_score']}</p>
        """
    return HttpResponse(code)

@login_required
def db_analyticstoreview(request):
    analytics = Analytic.objects.filter(status='REVIEW')
    
    code = f"""<h3>Analytics to review</h3>
        <p class="num"><a href="/qm/listanalytics/?statuses=REVIEW">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
def db_analyticspending(request):
    analytics = Analytic.objects.filter(status='PENDING')
    
    code = f"""<h3>Analytics pending</h3>
        <p class="num"><a href="/qm/listanalytics/?statuses=PENDING">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
def db_analyticswitherrors(request):
    analytics = Analytic.objects.filter(query_error=True).exclude(
        query_error_message__contains='"status":"FINISHED"').exclude(
        query_error_message__contains="'status': 'FINISHED'"
        ).exclude(status='ARCH')
    
    code = f"""<h3>Analytics with errors</h3>
        <p class="num"><a href="/reports/query_error">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
def db_archivedanalytics(request):
    analytics = Analytic.objects.filter(status='ARCH')
    
    code = f"""<h3>Archived analytics</h3>
        <p class="num"><a href="/admin/qm/analytic/?status__exact=ARCH">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
def db_runningtasks(request):
    tasks = TasksStatus.objects.all()
    
    code = f"""<h3>Running tasks</h3>
        <p class="num"><a href="/admin/qm/tasksstatus/">{tasks.count()}</p>
        """
    return HttpResponse(code)

@login_required
def db_top_endpoint_distinct_analytics(request):
    top_endpoints = (
        Endpoint.objects
        .values('hostname', 'site')
        .annotate(analytics_count=Count('snapshot__analytic', distinct=True))
        .order_by('-analytics_count')
    )
    
    code = f"""<h3>Most distinct analytics on single endpoint</h3>
        <p class="num"><a href="/reports/endpoints_most_analytics">{top_endpoints.first()['analytics_count']}</p>
        """
    return HttpResponse(code)

@login_required
def db_analyticsbystatus(request):
    status_breakdown = Analytic.objects.values('status').exclude(status='ARCH').annotate(count=Count('id'))
    context = { 'status_breakdown': status_breakdown, }
    return render(request, 'db_analyticsbystatus.html', context)        

@login_required
def db_analyticsbyconnector(request):
    connector_breakdown = Analytic.objects.values('connector__id', 'connector__name').exclude(status='ARCH').annotate(count=Count('id'))
    context = { 'connector_breakdown': connector_breakdown, }
    return render(request, 'db_analyticsbyconnector.html', context)        

@login_required
def db_analyticsbyuser(request):
    analytics_breakdown = Analytic.objects.values('created_by__id', 'created_by__username').exclude(status='ARCH').annotate(count=Count('id'))
    context = { 'analytics_breakdown': analytics_breakdown, }
    return render(request, 'db_analyticsbyuser.html', context)        


@login_required
def edit_description_initial(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    context = {
        "analytic_description": analytic.description,
        "analytic_id": analytic.id
    }
    return render(request, 'edit_description_initial.html', context)

@login_required
def edit_description_form(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    context = {
        "form": EditAnalyticDescriptionForm(initial={'description': analytic.description}),
        "analytic_id": analytic.id,
    }
    return render(request, 'edit_description_form.html', context)

@login_required
def edit_description_submit(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    if request.method == "POST":
        form = EditAnalyticDescriptionForm(request.POST, instance=analytic)
        if form.is_valid():
            form.save()
        else:
            return render(request, 'edit_description_form.html', {'analytic_id': analytic.id})
    return HttpResponseRedirect(f"/qm/edit_description_initial/{analytic.id}")

@login_required
def edit_notes_initial(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    context = {
        "analytic_notes": analytic.notes,
        "analytic_id": analytic.id
    }
    return render(request, 'edit_notes_initial.html', context)

@login_required
def edit_notes_form(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    context = {
        "form": EditAnalyticNotesForm(initial={'notes': analytic.notes}),
        "analytic_id": analytic.id,
    }
    return render(request, 'edit_notes_form.html', context)

@login_required
def edit_notes_submit(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    if request.method == "POST":
        form = EditAnalyticNotesForm(request.POST, instance=analytic)
        if form.is_valid():
            form.save()
        else:
            return render(request, 'edit_notes_form.html', {'analytic_id': analytic.id})
    return HttpResponseRedirect(f"/qm/edit_notes_initial/{analytic.id}")

@login_required
def edit_query_initial(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    context = {
        "analytic_query": analytic.query,
        "analytic_columns": analytic.columns,
        "analytic_id": analytic.id
    }
    return render(request, 'edit_query_initial.html', context)

@login_required
def edit_query_form(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    context = {
        "form": EditAnalyticQueryForm(
            initial={
                'query': analytic.query,
                'columns': analytic.columns
            }
        ),
        "analytic_id": analytic.id,
    }
    return render(request, 'edit_query_form.html', context)

@login_required
def edit_query_submit(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    if request.method == "POST":
        form = EditAnalyticQueryForm(request.POST, instance=analytic)
        if form.is_valid():
            form.save()
        else:
            return render(request, 'edit_query_form.html', {'analytic_id': analytic.id})
    return HttpResponseRedirect(f"/qm/edit_query_initial/{analytic.id}")

@login_required
def status_button(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    
    # List of statuses to be shown, depending on current status and defined workflow
    statuses = get_available_statuses(analytic)

    context = {
        "analytic": analytic,
        "statuses": statuses,
    }
    return render(request, 'status_button.html', context)

@login_required
def change_status(request, analytic_id, updated_status):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    
    # sanitize user input to only allow valid statuses
    if updated_status not in get_available_statuses(analytic):
        return HttpResponseForbidden("Invalid status")

    if updated_status == 'PUB_RUNDAILY':
        analytic.run_daily = True
        updated_status = 'PUB'
    if updated_status == 'PUB_NO_RUNDAILY':
        analytic.run_daily = False
        updated_status = 'PUB'

    analytic.status = updated_status
    analytic.save()
    
    context = {
        "analytic": analytic,
    }
    return render(request, 'status_button.html', context)

@login_required
def delete_analytic(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    analytic.delete()
    return HttpResponseRedirect(reverse('list_analytics'))

@login_required
def rundailycheckbox(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    if analytic.run_daily:
        if analytic.run_daily_lock:
            return HttpResponse('<img src="/static/images/lock.png" width="20" />')
        else:
            return HttpResponse('<img src="/static/admin/img/icon-yes.svg" />')
    else:
        return HttpResponse('<img src="/static/admin/img/icon-no.svg" />')


def review_page(request, analytic_id):
    form = ReviewForm()
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    reviews = Review.objects.filter(analytic=analytic).order_by('-date')
    context = {
        "form": form,
        "analytic": analytic,
        "reviews": reviews,
    }
    return render(request, 'review_page.html', context)


@login_required
def submit_review(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    form = ReviewForm(request.POST)

    if form.is_valid():
        reviews = Review.objects.filter(analytic=analytic).order_by('-date'),

        # commit set to False to simulate save and check errors
        review = form.save(commit=False)
        review.analytic = analytic
        review.reviewer = request.user
        review.save()

        if form.cleaned_data['decision'] == 'PENDING':
            analytic.status = 'PENDING'
            # run_daily flag will be set to False automatically (signals)
            analytic.next_review_date = None
            analytic.save()
        elif form.cleaned_data['decision'] == 'KEEP':
            analytic.status = 'PUB'
            # Bug #186 - "Keep it running" option during review should automatically enable "run_daily" flag if unset
            if not analytic.run_daily:
                analytic.run_daily = True
            # next_review_date will be set automatically (signals)
            analytic.save()
        elif form.cleaned_data['decision'] == 'LOCK':
            analytic.status = 'PUB'
            analytic.run_daily_lock = True
            analytic.next_review_date = None
            analytic.save()
        elif form.cleaned_data['decision'] == 'ARCH':
            analytic.status = 'ARCH'
            analytic.next_review_date = None
            # run_daily flag will be set to False automatically (signals)
            analytic.save()
        elif form.cleaned_data['decision'] == 'DEL':
            analytic.delete()

        return render(request, 'partials/review_form_success.html', {
            'analytic': analytic,
            'reviews': reviews,
        })
        
    else:
        return render(request, 'partials/review_form.html', {
            'analytic': analytic,
            'form': form,
        })
            
@login_required
def reviews_table(request, analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    reviews = Review.objects.filter(analytic=analytic).order_by('-date')
    return render(request, 'partials/reviews_table.html', {
        'analytic': analytic,
        'reviews': reviews,
    })
