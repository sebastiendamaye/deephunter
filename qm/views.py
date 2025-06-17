import requests
import json
from django.conf import settings
from time import sleep
from ldap3 import Server, Connection, ALL
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, FileResponse, JsonResponse
from django.db.models import Q, Sum
from urllib.parse import quote, quote_plus
from datetime import datetime, timedelta, date
import numpy as np
from scipy import stats
from .models import Country, Query, Snapshot, Campaign, TargetOs, Vulnerability, ThreatActor, ThreatName, MitreTactic, MitreTechnique, Endpoint, Tag, CeleryStatus, Category
from .tasks import regenerate_stats
import ipaddress
import re

VT_API_KEY = settings.VT_API_KEY
CUSTOM_FIELDS = settings.CUSTOM_FIELDS
BASE_DIR = settings.BASE_DIR
UPDATE_ON = settings.UPDATE_ON

# Params for requests API calls
S1_URL = settings.S1_URL
S1_TOKEN = settings.S1_TOKEN
PROXY = settings.PROXY
XDR_URL = settings.XDR_URL
XDR_PARAMS = settings.XDR_PARAMS
S1_THREATS_URL = settings.S1_THREATS_URL

# Params for LDAP3 calls
LDAP_SERVER = settings.LDAP_SERVER
LDAP_PORT = settings.LDAP_PORT
LDAP_SSL = settings.LDAP_SSL
LDAP_USER = settings.LDAP_USER
LDAP_PWD = settings.LDAP_PWD
LDAP_SEARCH_BASE = settings.LDAP_SEARCH_BASE
LDAP_ATTRIBUTES = settings.LDAP_ATTRIBUTES

# Params for S1 TOKEN
STATIC_PATH = settings.STATIC_ROOT
S1_TOKEN_EXPIRATION = settings.S1_TOKEN_EXPIRATION

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
            
        if 'star_rule' in request.POST:
            if request.POST['star_rule'] == '1':
                queries = queries.filter(star_rule=True)
                posted_filters['star_rule'] = 1
            else:
                queries = queries.filter(star_rule=False)
                posted_filters['star_rule'] = 0

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
            query.hits_c1 = snapshot.hits_c1
            query.hits_c2 = snapshot.hits_c2
            query.hits_c3 = snapshot.hits_c3
            query.hits_endpoints = snapshot.hits_endpoints
            query.hits_count = snapshot.hits_count
            query.anomaly_alert_count = snapshot.anomaly_alert_count
            query.anomaly_alert_endpoints = snapshot.anomaly_alert_endpoints
        else:
            query.hits_c1 = 0
            query.hits_c2 = 0
            query.hits_c3 = 0
            query.hits_endpoints = 0
            query.hits_count = 0
        
        # Sparkline: show sparkline only for last 20 days event count
        snapshots = Snapshot.objects.filter(query=query, date__gt=datetime.today()-timedelta(days=20))
        query.sparkline = [snapshot.hits_endpoints for snapshot in snapshots]

    custom_fields = []
    if CUSTOM_FIELDS['c1']:
        custom_fields.append(CUSTOM_FIELDS['c1']['name'])
    if CUSTOM_FIELDS['c2']:
        custom_fields.append(CUSTOM_FIELDS['c2']['name'])
    if CUSTOM_FIELDS['c3']:
        custom_fields.append(CUSTOM_FIELDS['c3']['name'])
    
    # Check if token is about to expire
    tokenexpires = 1000
    try:
        with open('{}/tokendate.txt'.format(STATIC_PATH), 'r') as f:
            d = re.search(r'\d{4}-\d{2}-\d{2}', f.readline())
            tokendate = datetime.strptime(d.group(), "%Y-%m-%d")
            tokenelapseddays = (datetime.today() - tokendate).days
            tokenexpires = S1_TOKEN_EXPIRATION - tokenelapseddays
    except:
        tokenexpires = 1000

    # Check if new version available
    try:
        update_available = False
        
        # remote version
        # update on new release only
        if UPDATE_ON == 'release':
            r = requests.get(
                'https://api.github.com/repos/sebastiendamaye/deephunter/releases/latest',
                proxies=PROXY
                )
            remote_ver = r.json()['name']
            # local version
            with open(f'{STATIC_PATH}/VERSION', 'r') as f:
                local_ver = f.readline().strip()
        else:
            # update on every new commit
            r = requests.get(
                'https://raw.githubusercontent.com/sebastiendamaye/deephunter/refs/heads/main/static/commit_id.txt',
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
        'custom_fields': custom_fields,
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
    a_c1 = np.array([snapshot.hits_c1 for snapshot in snapshots])
    a_c2 = np.array([snapshot.hits_c2 for snapshot in snapshots])
    a_c3 = np.array([snapshot.hits_c3 for snapshot in snapshots])
    a_anomaly_alert_count = np.array([snapshot.anomaly_alert_count for snapshot in snapshots])
    a_anomaly_alert_endpoints = np.array([snapshot.anomaly_alert_endpoints for snapshot in snapshots])
    if CUSTOM_FIELDS['c1']:
        c1_name = CUSTOM_FIELDS['c1']['name']
    else:
        c1_name = ''

    if CUSTOM_FIELDS['c2']:
        c2_name = CUSTOM_FIELDS['c2']['name']
    else:
        c2_name = ''

    if CUSTOM_FIELDS['c3']:
        c3_name = CUSTOM_FIELDS['c3']['name']
    else:
        c3_name = ''

    for i,v in enumerate(a_count):
        stats_vals.append( {
            'date': date[i],
            'runtime': runtime[i],
            'hits_count': a_count[i],
            'zscore_count': z_count[i],
            'hits_endpoints': a_endpoints[i],
            'zscore_endpoints': z_endpoints[i],
            'hits_c1': a_c1[i],
            'hits_c2': a_c2[i],
            'hits_c3': a_c3[i],
            'anomaly_alert_count': a_anomaly_alert_count[i],
            'anomaly_alert_endpoints': a_anomaly_alert_endpoints[i]
            } )
    
    context = {
        'query': query,
        'stats': stats_vals,
        'c1_name': c1_name,
        'c2_name': c2_name,
        'c3_name': c3_name,
        }
    return render(request, 'trend.html', context)

@login_required
def pq(request, query_id, site):
    query = get_object_or_404(Query, pk=query_id)
    if site==1 or site==2 or site==3:
        # site=1 means 1st custom field (C1), site=2 means 2nd custom field (C2), etc
        if site==1:
            custom_field = CUSTOM_FIELDS['c1']['filter']
        elif site==2:
            custom_field = CUSTOM_FIELDS['c2']['filter']
        elif site==3:
            custom_field = CUSTOM_FIELDS['c3']['filter']
        
        customized_query = "{} \n| filter {}".format(query.query, custom_field)
    else:
        customized_query = query.query
    
    if query.columns:
        q = quote('{}\n{}'.format(customized_query, query.columns))
    else:
        q = quote(customized_query)
    
    startdate = (datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
    return HttpResponseRedirect('{}/query?filter={}&{}&startTime={}&endTime=%2B1day'.format(XDR_URL, q.replace('%0D', ''), XDR_PARAMS, startdate))

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
    
    if CUSTOM_FIELDS['c1']:
        c1 = CUSTOM_FIELDS['c1']['description']
    else:
        c1 = ''
        
    if CUSTOM_FIELDS['c2']:
        c2 = CUSTOM_FIELDS['c2']['description']
    else:
        c2 = ''
    
    if CUSTOM_FIELDS['c3']:
        c3 = CUSTOM_FIELDS['c3']['description']
    else:
        c3 = ''
        
    context = {
        'q': query,
        'endpoints': endpoints,
        'progress': progress,
        'c1': c1,
        'c2': c2,
        'c3': c3        
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
                'storylineid': 'StorylineID: {}'.format(e.storylineid.replace('#', ', '))
                })
            storylineid_json[iid] = e.storylineid.split('#')
            iid += 1
        
        # Populate threats (group ID = 999 for easy identification in template)
        gid = 999
        createdat = (datetime.today()-timedelta(days=90)).isoformat()
        
        r = requests.get(
            '{}/web/api/v2.1/threats?computerName__contains={}&createdAt__gte={}'.format(S1_URL, hostname, createdat),
            params = {"limit": 100},
            headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
            proxies=PROXY
            )
        
        threats = r.json()['data']
        if threats:
            groups.append({'id':gid, 'content':'Threats (S1)'})
        
        for threat in threats:
            if threat['threatInfo']:
                #if threat['threatInfo']['analystVerdict'] != 'false_positive':
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

        # Populate applications (group ID = 998 for easy identification in template)
        gid = 998

        # Get machine ID
        r = requests.get(
            '{}/web/api/v2.1/agents?computerName={}'.format(S1_URL, hostname),
            headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
            proxies=PROXY
            )
        try:
            machinedetails = r.json()['data'][0]
            id = r.json()['data'][0]['id']
            username = ''

            if id:
                # Get username
                r = requests.get(
                    '{}/web/api/v2.1/agents?ids={}'.format(S1_URL, id),
                    headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
                    proxies=PROXY
                    )
                username = r.json()['data'][0]['lastLoggedInUserName']
            
                groups.append({'id':gid, 'content':'Apps install (S1)'})
                
                createdat = (datetime.today()-timedelta(days=90))
                # Get applications
                
                r = requests.get(
                    '{}/web/api/v2.1/agents/applications?ids={}'.format(S1_URL, id),
                    headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
                    proxies=PROXY
                    )
                apps = r.json()['data']
                
                for app in apps:
                    if app['installedDate']:
                        if datetime.strptime(app['installedDate'][:10], '%Y-%m-%d') >= createdat:
                            items.append({
                                'id': iid,
                                'group': gid,
                                'start':  datetime.strptime(app['installedDate'][:10], '%Y-%m-%d'),
                                'end': datetime.strptime(app['installedDate'][:10], '%Y-%m-%d')+timedelta(days=1),
                                'description': '{} ({})'.format(app['name'], app['publisher'])
                                })
                            iid += 1
                
                # Get user info from AD
                user_name = 'N/A'
                job_title = 'N/A'
                business_unit = 'N/A'
                location = 'N/A'
                if LDAP_SERVER:
                    server = Server(LDAP_SERVER, port=LDAP_PORT, use_ssl=LDAP_SSL, get_info=ALL)
                    conn = Connection(server, LDAP_USER, LDAP_PWD, auto_bind=True)
                    conn.search(
                        LDAP_SEARCH_BASE,
                        '(sAMAccountName={})'.format(username),
                        attributes=[
                            LDAP_ATTRIBUTES['USER_NAME'],
                            LDAP_ATTRIBUTES['JOB_TITLE'],
                            LDAP_ATTRIBUTES['BUSINESS_UNIT'],
                            LDAP_ATTRIBUTES['OFFICE'],
                            LDAP_ATTRIBUTES['COUNTRY']
                            ]
                        )
                    if conn.entries:
                        entry = conn.entries[0]
                        user_name = entry.displayName
                        job_title = entry.title
                        business_unit = entry.division
                        location = "{}, {}".format(entry.physicalDeliveryOfficeName, entry.co)
                    
        except:
            username = ''
            machinedetails = ''
            apps = ''
            user_name = ''
            job_title = ''
            business_unit = ''
            location = ''

        # Visualization #2 (graph)
        items2 = Endpoint.objects.filter(hostname=hostname) \
            .values('snapshot__date') \
            .annotate(cumulative_score=Sum('snapshot__query__weighted_relevance')) \
            .order_by('snapshot__date')

    else:
        hostname = ''
        username = ''
        machinedetails = ''
        apps = ''
        user_name = ''
        job_title = ''
        business_unit = ''
        location = ''
    
    
    
    context = {
        'S1_THREATS_URL': S1_THREATS_URL.format(hostname),
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
def events(request, endpointname, query_id, eventdate):    
    query = get_object_or_404(Query, pk=query_id)
    if endpointname != 'NULL':
        customized_query = "{} \n| filter endpoint.name='{}'".format(query.query, endpointname)
    else:
        customized_query = query.query

    if query.columns:
        q = quote('{}\n{}'.format(customized_query, query.columns))
    else:
        q = quote(customized_query)
    
    return HttpResponseRedirect('{}/query?filter={}&startTime={}&endTime=%2B1+day&{}'.format(XDR_URL, q.replace('%0D', ''), eventdate, XDR_PARAMS))

@login_required
def storyline(request, storylineids, eventdate):    
    if ',' in storylineids:
        filter = "src.process.storyline.id in {}".format(tuple(storylineids.split(',')))
    else:
        filter = f"src.process.storyline.id = '{storylineids}'"
    return HttpResponseRedirect('{}/events?filter={}&startTime={}&endTime=%2B1+day&{}'.format(XDR_URL, quote_plus(filter), eventdate, XDR_PARAMS))

@login_required
@permission_required("qm.delete_campaign")
def regen(request, query_id):
    query = get_object_or_404(Query, pk=query_id)
    id = regenerate_stats.delay(query_id)
    return HttpResponse('Celery Task ID: {}'.format(id))

@login_required
@permission_required("qm.delete_campaign")
def progress(request, query_id):
    try:
        query = get_object_or_404(Query, pk=query_id)
        celery_status = get_object_or_404(CeleryStatus, query=query)
        return HttpResponse('<span><b>Task progress:</b> {}%</span>'.format(round(celery_status.progress)))
    except:
        return HttpResponse('<a href="{}/regen/" target="_blank" class="buttonred">Regenerate stats</a>'.format(query_id))

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
            query = "| join ("
            if hostname:
                query += "endpoint.name = '{}' and ".format(hostname)
            if storylineid:
                query += "src.process.storyline.id = '{}' and ".format(storylineid)
            query += """
event.category = 'ip' 
and dst.ip.address != '127.0.0.1' 
| group nbevents=count(), dstports=hacklist(dst.port.number) by dst.ip.address 
), ( 
| group nbhosts=estimate_distinct(endpoint.name) by dst.ip.address 
) on dst.ip.address 
| sort nbhosts
"""
            body = {
                'fromDate': (datetime.now() - timedelta(hours=timerange)).isoformat(),
                'query': query,
                'toDate': datetime.now().isoformat(),
                'limit': 100
            }
                    
            r = requests.post('{}/web/api/v2.1/dv/events/pq'.format(S1_URL),
                json=body,
                headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
                proxies=PROXY)
            
            try:
                query_id = r.json()['data']['queryId']
                status = r.json()['data']['status']
            
                # Ping PowerQuery every second, until it is complete (unless you do that, the PQ will be cancelled)
                while status == 'RUNNING':
                    r = requests.get('{}/web/api/v2.1/dv/events/pq-ping'.format(S1_URL),
                        params = {"queryId": query_id},
                        headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
                        proxies=PROXY)
                        
                    status = r.json()['data']['status']
                    progress = r.json()['data']['progress']
                    
                    sleep(1)

                if len(r.json()['data']['data']) != 0:
                    data = r.json()['data']['data']
                    headers = {
                        'x-apikey': VT_API_KEY,
                        'accept': 'application/json'
                        }
                    for ip in data:
                        
                        # if private ip, don't scan with VT
                        if ipaddress.ip_address(ip[0]).is_private:
                            iptype = 'PRIV'
                            vt = ''
                        else:
                            iptype = 'PUBL'
                            vt = {}
                            response = requests.get(
                                "https://www.virustotal.com/api/v3/ip_addresses/{}".format(ip[0]),
                                headers=headers,
                                proxies=PROXY
                                )
                            vt['malicious'] = response.json()['data']['attributes']['last_analysis_stats']['malicious']
                            vt['suspicious'] = response.json()['data']['attributes']['last_analysis_stats']['suspicious']
                            vt['whois'] = response.json()['data']['attributes']['whois']
                        
                        ips.append({
                            'dstip': ip[0],
                            'iptype': iptype,
                            'dstports': ip[2],
                            'freq': int(ip[3]),
                            'vt': vt
                            })
                
            except:
                debug = ''
            #except Exception as e: 
            #    debug = "***REQUEST FAILED: {}".format(e)
       
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
    messages.add_message(request, messages.INFO, "DeepHunter will soon become ARTHIX!")
    
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
