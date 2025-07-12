import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q, Sum
from datetime import datetime, timedelta, timezone
import logging
import numpy as np
from scipy import stats
from .models import Country, Query, Snapshot, Campaign, TargetOs, Vulnerability, ThreatActor, ThreatName, MitreTactic, MitreTechnique, Endpoint, Tag, CeleryStatus, Category
from connectors.models import Connector
from .tasks import regenerate_stats
import ipaddress
from connectors.utils import is_connector_enabled, get_connector_conf
from celery import current_app

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

# Get an instance of a logger
logger = logging.getLogger(__name__)


@login_required
def index(request):
    queries = Query.objects.all()
    
    posted_search = ''
    posted_filters = {}
    
    if request.POST:
        
        if 'search' in request.POST:
            queries = queries.filter(
                Q(name__icontains=request.POST['search'])
                | Q(description__icontains=request.POST['search'])
                | Q(notes__icontains=request.POST['search'])
            )
            posted_search = request.POST['search']
            
        if 'connectors' in request.POST:
            queries = queries.filter(connector__pk__in=request.POST.getlist('connectors'))
            posted_filters['connectors'] = request.POST.getlist('connectors')

        if 'categories' in request.POST:
            queries = queries.filter(category__pk__in=request.POST.getlist('categories'))
            posted_filters['categories'] = request.POST.getlist('categories')

        if 'target_os' in request.POST:
            queries = queries.filter(target_os__pk__in=request.POST.getlist('target_os'))
            posted_filters['target_os'] = request.POST.getlist('target_os')
        
        if 'vulnerabilities' in request.POST:
            queries = queries.filter(vulnerabilities__pk__in=request.POST.getlist('vulnerabilities'))
            posted_filters['vulnerabilities'] = request.POST.getlist('vulnerabilities')
        
        if 'tags' in request.POST:
            queries = queries.filter(tags__pk__in=request.POST.getlist('tags'))
            posted_filters['tags'] = request.POST.getlist('tags')
        
        if 'actors' in request.POST:
            queries = queries.filter(actors__pk__in=request.POST.getlist('actors'))
            posted_filters['actors'] = request.POST.getlist('actors')
        
        if 'source_countries' in request.POST:
            # List of all APT associated to the selected source countries
            apt = []
            for countryid in request.POST.getlist('source_countries'):
                country = get_object_or_404(Country, pk=countryid)
                for i in ThreatActor.objects.filter(source_country=country):
                    apt.append(i.id)
            queries = queries.filter(actors__pk__in=apt)
            posted_filters['source_countries'] = request.POST.getlist('source_countries')
        
        if 'threats' in request.POST:
            queries = queries.filter(threats__pk__in=request.POST.getlist('threats'))
            posted_filters['threats'] = request.POST.getlist('threats')
        
        if 'mitre_techniques' in request.POST:
            queries = queries.filter(mitre_techniques__pk__in=request.POST.getlist('mitre_techniques'))
            posted_filters['mitre_techniques'] = request.POST.getlist('mitre_techniques')
        
        if 'mitre_tactics' in request.POST:
            queries = queries.filter(mitre_techniques__mitre_tactic__pk__in=request.POST.getlist('mitre_tactics'))
            posted_filters['mitre_tactics'] = request.POST.getlist('mitre_tactics')
        
        if 'confidence' in request.POST:
            queries = queries.filter(confidence__in=request.POST.getlist('confidence'))
            posted_filters['confidence'] = request.POST.getlist('confidence')
        
        if 'relevance' in request.POST:
            queries = queries.filter(relevance__in=request.POST.getlist('relevance'))
            posted_filters['relevance'] = request.POST.getlist('relevance')

        if 'status' in request.POST:
            queries = queries.filter(pub_status__in=request.POST.getlist('status'))
            posted_filters['status'] = request.POST.getlist('status')
            
        if 'run_daily' in request.POST:
            if request.POST['run_daily'] == '1':
                queries = queries.filter(run_daily=True)
                posted_filters['run_daily'] = 1
            else:
                queries = queries.filter(run_daily=False)
                posted_filters['run_daily'] = 0
            
        if 'create_rule' in request.POST:
            if request.POST['create_rule'] == '1':
                queries = queries.filter(create_rule=True)
                posted_filters['create_rule'] = 1
            else:
                queries = queries.filter(create_rule=False)
                posted_filters['create_rule'] = 0

        if 'dynamic_query' in request.POST:
            if request.POST['dynamic_query'] == '1':
                queries = queries.filter(dynamic_query=True)
                posted_filters['dynamic_query'] = 1
            else:
                queries = queries.filter(dynamic_query=False)
                posted_filters['dynamic_query'] = 0

        if 'hits' in request.POST:
            # Get yesterday's date
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_date = yesterday.date()  # Get the date part

            if request.POST['hits'] == '1':
                # Filter queries where related Snapshot has hits_count > 0 and date is yesterday
                queries = queries.filter(
                    snapshot__hits_count__gt=0,
                    snapshot__date=yesterday_date
                ).distinct()
                posted_filters['hits'] = 1
            else:
                # Filter queries where related Snapshot has hits_count = 0 and date is yesterday
                queries = queries.filter(
                    snapshot__hits_count=0,
                    snapshot__date=yesterday_date
                ).distinct()
                posted_filters['hits'] = 0

        if 'maxhosts' in request.POST:
            if request.POST['maxhosts'] == '1':
                queries = queries.filter(maxhosts_count__gt=0)
                posted_filters['maxhosts'] = 1
            else:
                queries = queries.filter(maxhosts_count=0)
                posted_filters['maxhosts'] = 0

        if 'queryerror' in request.POST:
            if request.POST['queryerror'] == '1':
                queries = queries.filter(query_error=True)
                posted_filters['queryerror'] = 1
            else:
                queries = queries.filter(query_error=False)
                posted_filters['queryerror'] = 0

        if 'created_by' in request.POST:
            queries = queries.filter(created_by__pk__in=request.POST.getlist('created_by'))
            posted_filters['created_by'] = request.POST.getlist('created_by')

    for query in queries:
        #snapshot = Snapshot.objects.filter(query=query, date__gt=datetime.today()-timedelta(days=1)).order_by('date')
        snapshot = Snapshot.objects.filter(query=query, date=datetime.today()-timedelta(days=1)).order_by('date')
        if len(snapshot) > 0:
            snapshot = snapshot[0]
            query.hits_endpoints = snapshot.hits_endpoints
            query.hits_count = snapshot.hits_count
            query.anomaly_alert_count = snapshot.anomaly_alert_count
            query.anomaly_alert_endpoints = snapshot.anomaly_alert_endpoints
        else:
            query.hits_endpoints = 0
            query.hits_count = 0
        
        # Sparkline: show sparkline only for last 20 days event count
        snapshots = Snapshot.objects.filter(query=query, date__gt=datetime.today()-timedelta(days=20))
        query.sparkline = [snapshot.hits_endpoints for snapshot in snapshots]
        
    # Check if token is about to expire
    tokenexpires = 999
    if is_connector_enabled('sentinelone'):
        expires_on = all_connectors.get('sentinelone').get_token_expiration_date()
        if expires_on:
            dt = datetime.strptime(expires_on, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = dt - now
            tokenexpires = delta.days + 1    

    # Check if new version available
    try:
        update_available = False
        
        # remote version
        # update on new release only
        if UPDATE_ON == 'release':
            r = requests.get(
                GITHUB_LATEST_RELEASE_URL,
                proxies=PROXY
                )
            remote_ver = r.json()['name']
            # local version
            with open(f'{STATIC_PATH}/VERSION', 'r') as f:
                local_ver = f.readline().strip()
        else:
            # update on every new commit
            r = requests.get(
                GITHUB_COMMIT_URL,
                proxies=PROXY
                )
            remote_ver = r.text.strip()
            # local version
            with open(f'{STATIC_PATH}/commit_id.txt', 'r') as f:
                local_ver = f.readline().strip()
            
        # compare
        if local_ver != remote_ver:
            update_available = True
            
    except:
        update_available = False

    context = {
        'queries': queries,
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
        'created_by': User.objects.filter(id__in=Query.objects.exclude(created_by__isnull=True).values('created_by').distinct()),
        'posted_search': posted_search,
        'posted_filters': posted_filters,
        'tokenexpires': tokenexpires,
        'update_available': update_available
    }
    return render(request, 'list_queries.html', context)
    
@login_required
def trend(request, query_id):
    query = get_object_or_404(Query, pk=query_id)
    # show graph for last 90 days only
    snapshots = Snapshot.objects.filter(query = query, date__gt=datetime.today()-timedelta(days=90))
    
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

    endpoints = Endpoint.objects.filter(snapshot__query=query).values('hostname').distinct()

    context = {
        'query': query,
        'stats': stats_vals,
        'distinct_endpoints': endpoints.count(),
        'endpoints': endpoints,
        }
    return render(request, 'trend.html', context)

@login_required
def querydetail(request, query_id):
    query = get_object_or_404(Query, pk=query_id)    
    
    # Populate the list of endpoints (top 10) that matched the query for the last campaign
    try:
        #snapshots = Snapshot.objects.filter(query=query, date__gt=datetime.today()-timedelta(days=1))
        snapshots = Snapshot.objects.filter(query=query, date=datetime.today()-timedelta(days=1))
        endpoints = []
        for snapshot in snapshots:
            for e in Endpoint.objects.filter(snapshot=snapshot):
                endpoints.append(e.hostname)
        # remove duplicated values (due to endpoints appearing in several snapshots)
        endpoints = list(set(endpoints))[:10]
    except:
        endpoints = []

    # get celery status for the selected query
    try:
        celery_status = get_object_or_404(CeleryStatus, query=query)
        progress = round(celery_status.progress)
    except:
        progress = 999
            
    context = {
        'q': query,
        'endpoints': endpoints,
        'progress': progress
        }
    return render(request, 'query_detail.html', context)

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
            g = next((group for group in groups if group['content'] == e.snapshot.query.name), None)
            # if group does not exist yet, create it
            if g:
                g = g['id']
            else:
                groups.append({'id':gid, 'qid':e.snapshot.query.id, 'content':e.snapshot.query.name})
                g = gid
                gid += 1
                
            # populate items and refer to relevant group
            items.append({
                'id': iid,
                'group': g,
                'start': e.snapshot.date,
                'end': e.snapshot.date+timedelta(days=1),
                'description': 'Signature: {}'.format(e.snapshot.query.name),
                'connector': 'Connector: {}'.format(e.snapshot.query.connector.name),
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
                    groups.append({'id':gid, 'content':'Apps install (S1)'})
                    
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
            .annotate(cumulative_score=Sum('snapshot__query__weighted_relevance')) \
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
def events(request, query_id, eventdate=None, endpointname=None):
    """
    Redirect to the query link in the connector's data lake.
    """
    query = get_object_or_404(Query, pk=query_id)
    return HttpResponseRedirect(all_connectors.get(query.connector.name).get_redirect_query_link(query, eventdate, endpointname))

@login_required
def storyline(request, storylineids, eventdate):
    """
    Redirect to Singularity DataLake in S1 with results related to the queried storyline ID(s).
    Only relevant for SentinelOne connector.
    """
    return HttpResponseRedirect(all_connectors.get('sentinelone').get_redirect_storyline_link(storylineids, eventdate))

@login_required
@permission_required("qm.delete_campaign")
def regen(request, query_id):
    query = get_object_or_404(Query, pk=query_id)
    
    # Create task in CeleryStatus object
    celery_status = CeleryStatus(
        query=query,
        progress=0
        )
    celery_status.save()    
    
    # start the celery task (defined in qm/tasks.py)
    taskid = regenerate_stats.delay(query_id)

    # Update CeleryStatus with the task ID
    celery_status.taskid = taskid
    celery_status.save()

    return HttpResponse('Celery Task ID: {}'.format(taskid))

@login_required
@permission_required("qm.delete_campaign")
def cancelregen(request, taskid):
    try:
        # without signal='SIGKILL', the task is not cancelled immediately
        current_app.control.revoke(taskid, terminate=True, signal='SIGKILL')
        # delete task in DB
        celery_status = get_object_or_404(CeleryStatus, taskid=taskid)
        celery_status.delete()
        return HttpResponse('Celery Task terminated')
    except Exception as e:
        logging.error(f"Revoke failed: {e}")
        return HttpResponse('Error terminating Celery Task: {}'.format(e))

@login_required
@permission_required("qm.delete_campaign")
def progress(request, query_id):
    try:
        query = get_object_or_404(Query, pk=query_id)
        celery_status = get_object_or_404(CeleryStatus, query=query)
        return HttpResponse('<span><b>Task progress:</b> {}% | <a href="/cancelregen/{}/" target="_blank">CANCEL</a></span>'.format(round(celery_status.progress), celery_status.taskid))
    except:
        return HttpResponse('<a href="/{}/regen/" target="_blank" class="buttonred">Regenerate stats</a>'.format(query_id))

@login_required
@permission_required("qm.delete_campaign")
def deletestats(request, query_id):
    query = get_object_or_404(Query, pk=query_id)
    Snapshot.objects.filter(query=query).delete()
    return HttpResponseRedirect('/')

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
