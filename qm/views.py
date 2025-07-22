import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from datetime import datetime, timedelta, timezone
import logging
import numpy as np
from scipy import stats
from math import isnan
from .models import Country, Analytic, Snapshot, Campaign, TargetOs, Vulnerability, ThreatActor, ThreatName, MitreTactic, MitreTechnique, Endpoint, Tag, TasksStatus, Category
from connectors.models import Connector
from .tasks import regenerate_stats, regenerate_campaign
import ipaddress
from connectors.utils import is_connector_enabled, get_connector_conf
from celery import current_app
from qm.utils import get_campaign_date
from urllib.parse import urlencode

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
DISABLE_RUN_DAILY_ON_ERROR = settings.DISABLE_RUN_DAILY_ON_ERROR
ANALYTICS_PER_PAGE = settings.ANALYTICS_PER_PAGE

# Get an instance of a logger
logger = logging.getLogger(__name__)


@login_required
def index(request):
    analytics = Analytic.objects.all()
    
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
            analytics = analytics.filter(mitre_techniques__pk__in=request.GET.getlist('mitre_techniques'))
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

        if 'status' in request.GET:
            analytics = analytics.filter(pub_status__in=request.GET.getlist('status'))
            posted_filters['status'] = request.GET.getlist('status')
            
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

    context = {
        'analytics': page_obj,
        'query_string': query_string,
        'analytics_count': analytics_count,
        'connectors': Connector.objects.filter(visible_in_analytics=True),
        'target_os': TargetOs.objects.all(),
        'vulnerabilities': Vulnerability.objects.all(),
        'tags': Tag.objects.all(),
        'threat_actors': ThreatActor.objects.all(),
        'source_countries': Country.objects.all(),
        'threat_names': ThreatName.objects.all(),
        'mitre_tactics': MitreTactic.objects.all(),
        'mitre_techniques': MitreTechnique.objects.all(),
        'categories': Category.objects.all(),
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
@permission_required("qm.delete_campaign")
def debug(request):
    f = open('{}/campaigns.log'.format(BASE_DIR), 'r', encoding='utf-8', errors='replace')
    context = {'debug': f.read()}
    return render(request, 'debug.html', context)

@login_required
def timeline(request):
    groups = []
    items = []
    items2 = []
    gid = 0 # group id
    iid = 0 # item id
    storylineid_json = {}

    hostname = ''
    username = ''
    machinedetails = ''
    apps = ''
    user_name = ''
    job_title = ''
    business_unit = ''
    location = ''

    if request.GET:
        hostname = request.GET['hostname'].strip()
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
            iid += 1
        

        # Populate threats (group ID = 999 for easy identification in template)
        gid = 999
        created_at = (datetime.today()-timedelta(days=DB_DATA_RETENTION)).isoformat()

        # Recursively call the get_threats function in each connector to build a consolidated list of threats
        for connector in all_connectors.values():
        
            if hasattr(connector, 'get_threats'):
                # If the connector has a get_threats method, call it
                #try:
                threats = connector.get_threats(hostname, created_at)
                if threats:
                    groups.append({'id':gid, 'content':f'Threats ({connector.__name__.split(".")[1]})'})
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
                            'storylineid': 'StorylineID: {}'.format(threat['threatInfo']['storyline'])
                            })
                        storylineid_json[iid] = [threat['threatInfo']['storyline']]
                        iid += 1
                """except Exception as e:
                    print(f"Error getting threats for {hostname}")"""

        ###
        # The below content is only available if SentinelOne connector is enabled
        ###
        if is_connector_enabled('sentinelone'):

            username = ''

            # Get machine details from SentinelOne            
            machinedetails = all_connectors.get('sentinelone').get_machine_details(hostname)
            if machinedetails:
                agent_id = machinedetails['id']

                if agent_id:
                    # Get username
                    username = all_connectors.get('sentinelone').get_last_logged_in_user(agent_id)
                
                    # Populate applications (group ID = 998 for easy identification in template)
                    gid = 998
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
                    
                    # Get user info from AD
                    user_name = 'N/A'
                    job_title = 'N/A'
                    business_unit = 'N/A'
                    location = 'N/A'

                    entry = all_connectors.get('activedirectory').ldap_search(username)
                    if entry:
                        user_name = entry.displayName
                        job_title = entry.title
                        business_unit = entry.division
                        location = "{}, {}".format(entry.physicalDeliveryOfficeName, entry.co)
                    

        # Visualization #2 (graph)
        items2 = Endpoint.objects.filter(hostname=hostname) \
            .values('snapshot__date') \
            .annotate(cumulative_score=Sum('snapshot__analytic__weighted_relevance')) \
            .order_by('snapshot__date')

    
    context = {
        'S1_THREATS_URL': get_connector_conf('sentinelone', 'S1_THREATS_URL').format(hostname),
        'hostname': hostname,
        'username': username,
        'machinedetails': machinedetails,
        'apps': apps,
        'groups': groups,
        'items': items,
        'items2': items2,
        'mindate': datetime.today()-timedelta(days=91),
        'maxdate': datetime.today()+timedelta(days=1),
        'user_name': user_name,
        'job_title': job_title,
        'business_unit': business_unit,
        'location': location,
        'storylineid_json': storylineid_json
        }
    return render(request, 'timeline.html', context)

@login_required
def events(request, analytic_id, eventdate=None, endpointname=None):
    """
    Redirect to the analytic link in the connector's data lake.
    """
    analytic = get_object_or_404(Analytic, pk=analytic_id)
    return HttpResponseRedirect(all_connectors.get(analytic.connector.name).get_redirect_analytic_link(analytic, eventdate, endpointname))

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
        logging.error(f"Revoke failed: {e}")
        return HttpResponse('Error terminating Celery Task: {}'.format(e))

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
    messages.add_message(request, messages.INFO, "DeepHunter will always remain DeepHunter!")
    
    # local version
    with open(f'{STATIC_PATH}/VERSION', 'r') as f:
        version = f.readline().strip()
    
    context = {
        'version': version
        }
    return render(request, 'about.html', context)

@login_required
def notifications(request):
    context = {}
    return render(request, 'notifications.html', context)


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
def analytic_review(request, analytic_id):
    context = {'analytic_id': analytic_id}
    return render(request, 'analytic_review.html', context)
    