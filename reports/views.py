from django.conf import settings
import json
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseRedirect, FileResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum, Count
from urllib.parse import quote
from datetime import datetime, timedelta, date
from qm.models import Country, Query, Snapshot, Campaign, TargetOs, Vulnerability, ThreatActor, ThreatName, MitreTactic, MitreTechnique, Endpoint, Tag, CeleryStatus

# Params for requests API calls
XDR_URL = settings.XDR_URL
XDR_PARAMS = settings.XDR_PARAMS
# Params for MITRE JSON file
STATIC_PATH = settings.STATIC_ROOT
# DB retention
DB_DATA_RETENTION = settings.DB_DATA_RETENTION
# max hosts threshold
ON_MAXHOSTS_REACHED = settings.ON_MAXHOSTS_REACHED
# threshold for rare occurrences
RARE_OCCURRENCES_THRESHOLD = settings.RARE_OCCURRENCES_THRESHOLD

@login_required
def campaigns_stats(request):
    stats = []
    seconds_in_day = 24 * 60 * 60
    
    for i in reversed(range(DB_DATA_RETENTION)):
        d = date.today() - timedelta(days=i)
        try:
            campaign = Campaign.objects.get(
                name__startswith="daily_cron_",
                date_start__gte=timezone.now().replace(year=d.year, month=d.month, day=d.day, hour=0, minute=0, second=0),
                date_start__lte=timezone.now().replace(year=d.year, month=d.month, day=d.day, hour=23, minute=59, second=59)
                )        
            difference = campaign.date_end - campaign.date_start
            dur = divmod(difference.days * seconds_in_day + difference.seconds, 60)
            duration = round(dur[0]+dur[1]*5/3/100, 1)
            
            count_endpoints = Endpoint.objects.filter(snapshot__campaign=campaign).count()
            
            stats.append({
                'date':d,
                'count_analytics':campaign.nb_queries,
                'duration':duration,
                'count_endpoints':count_endpoints
                })
        except:
            stats.append({
                'date':d,
                'count_analytics':0,
                'duration':0,
                'count_endpoints':0
                })
    
    context = {
        'stats': stats,
        'db_retention': DB_DATA_RETENTION
        }
    
    return render(request, 'stats.html', context)

@login_required
def mitre(request):
    max_score = 0
    json = """
{
    "name": "layer",
    "versions": {
        "attack": "13",
        "navigator": "4.8.2",
        "layer": "4.4"
    },
    "domain": "enterprise-attack",
    "description": "",
    "filters": {
        "platforms": [
            "Linux",
            "macOS",
            "Windows",
            "Network",
            "PRE",
            "Containers",
            "Office 365",
            "SaaS",
            "Google Workspace",
            "IaaS",
            "Azure AD"
        ]
    },
    "sorting": 0,
    "layout": {
        "layout": "side",
        "aggregateFunction": "average",
        "showID": false,
        "showName": true,
        "showAggregateScores": true,
        "countUnscored": false
    },
    "hideDisabled": false,
    "techniques": [
"""
    
    t = []
    for technique in MitreTechnique.objects.all():
        score = Query.objects.filter(mitre_techniques=technique).count()
        t.append({
            "techniqueID": technique.mitre_id,
            "score": score
        })
        if score > max_score:
            max_score = score
    
    json += ',\n'.join([str(i).replace('\'', '"') for i in t])
    
    json += """
    ],
    "gradient": {
        "colors": [
            "#ff6666ff",
            "#ffe766ff",
            "#8ec843ff"
        ],
        "minValue": 0,
        "maxValue": """
    json += str(max_score)
    json += """
    },
    "legendItems": [],
    "metadata": [],
    "links": [],
    "showTacticRowBackground": false,
    "tacticRowBackground": "#dddddd",
    "selectTechniquesAcrossTactics": true,
    "selectSubtechniquesWithParent": false
}
"""
    # Write JSON file to static
    with open('{}/mitre.json'.format(STATIC_PATH), 'w') as mitrejsonfile:
        mitrejsonfile.write(json)
    
    # Build MITRE coverage
    ttp = []
    tactics = MitreTactic.objects.all()
    for tactic in tactics:
        techniques = MitreTechnique.objects.filter(mitre_tactic=tactic, is_subtechnique=False)
        print("Tactic: {} {} techniques".format(tactic.mitre_id, techniques.count()))
        
        tmp = []
        for technique in techniques:
            # how many analytics are using each technique or subtechniques related to the technique
            numqueries = Query.objects.filter(
                Q(mitre_techniques__mitre_id = technique.mitre_id)
                | Q(mitre_techniques__mitre_technique__mitre_id = technique.mitre_id)
            ).distinct().count()
            tmp.append({
                'mitre_id': technique.mitre_id,
                'name': technique.name,
                'numqueries': numqueries
                })
            
        ttp.append({
            'mitre_id': tactic.mitre_id,
            'name': tactic.name,
            'techniques': tmp
            })

    context = {
        'ttp': ttp
        }
    
    return render(request, 'mitre.html', context)

@login_required
def endpoints(request):
    # select TOP 20 endpoints for today's campaign
    endpoints = Endpoint.objects.filter(
        snapshot__date=datetime.today()-timedelta(days=1)
        ).values('hostname', 'site').annotate(total=Sum('snapshot__query__weighted_relevance')).order_by('-total')[:20]
    data = []
    for endpoint in endpoints:
        hostname = endpoint['hostname']
        site = endpoint['site']
        queries = Endpoint.objects.filter(
            snapshot__date=datetime.today()-timedelta(days=1),
            hostname=hostname
            ).order_by('-snapshot__query__weighted_relevance')
        
        qdata = []
        for query in queries:
            
            if '| parse' in query.snapshot.query.query or '| let' in query.snapshot.query.query or '| filter' in query.snapshot.query.query:
                # if there are embedded functions like "| parse", "| filter", etc... end of parenthesis should be
                # placed before the "| parse" statement, instead of at the very end of the query.
                customized_query = "endpoint.name='{}' and (\n{}".format(hostname, query.snapshot.query.query)
                # replace only the first occurence, not all where pipe is detected
                customized_query = customized_query.replace("| ", ")\n| ", 1)
            else:
                customized_query = "endpoint.name='{}' and (\n{}\n)".format(hostname, query.snapshot.query.query)
            
            if query.snapshot.query.columns:
                q = quote('{}\n{}'.format(customized_query, query.snapshot.query.columns))
            else:
                q = quote(customized_query)
            
            startdate=(datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
            xdrlink = '{}/query?filter={}&{}&startTime={}&endTime=%2B1day'.format(XDR_URL, q.replace('%0D', ''), XDR_PARAMS, startdate)
            
            qdata.append({
                "queryid":query.snapshot.query.id,
                "name":query.snapshot.query.name,
                "confidence":query.snapshot.query.confidence,
                "relevance":query.snapshot.query.relevance,
                "xdrlink":xdrlink
                })
        
        data.append({
            "hostname":hostname,
            "site":site,
            "total":endpoint['total'],
            "queries":qdata
            })
    context = {
        'endpoints': data
        }
    
    return render(request, 'endpoints.html', context)


@login_required
def missing_mitre(request):
    # Number of analytics with unmapped MITRE techniques
    q_unmapped = Query.objects.filter(mitre_techniques=None)
    q_unmapped_count = q_unmapped.count()

    # Number of analytics with MITRE techniques mapped
    q_mapped_count = Query.objects.filter(~Q(mitre_techniques=None)).count()

    context = {
        'q_unmapped': q_unmapped,
        'q_unmapped_count': q_unmapped_count,
        'q_mapped_count': q_mapped_count
        }
    
    return render(request, 'missing_mitre.html', context)

@login_required
def analytics_perfs(request):
    yesterday = datetime.now() - timedelta(days=1)
    snapshots = Snapshot.objects.filter(date=yesterday).order_by('-runtime')
    queries = []
    
    for snapshot in snapshots:
        query_snapshots = Snapshot.objects.filter(query=snapshot.query, date__gt=datetime.today()-timedelta(days=20)).order_by('date')
        queries.append({
                'id': snapshot.query.id,
                'name': snapshot.query.name,
                'runtime': snapshot.runtime,
                'sparkline': [query_snapshot.runtime for query_snapshot in query_snapshots]
            })
    
    context = {
        'queries': queries
        }
    
    return render(request, 'perfs.html', context)

@login_required
def disabled_analytics(request):
    queries = Query.objects.filter(
        run_daily = False,
        maxhosts_count__gte = ON_MAXHOSTS_REACHED['THRESHOLD']
    )
    context = {
        'queries': queries
        }
    
    return render(request, 'disabled_analytics.html', context)

@login_required
def query_error(request):
    queries = Query.objects.filter(query_error = True)
    context = {
        'queries': queries
        }
    
    return render(request, 'query_error.html', context)

@login_required
def rare_occurrences(request):
    queries = (
        Endpoint.objects
        .values('snapshot__query__id', 'snapshot__query__name', 'snapshot__query__confidence', 'snapshot__query__relevance', 'snapshot__query__description', 'snapshot__query__query')
        .annotate(distinct_hostnames=Count('hostname', distinct=True))
        .filter(distinct_hostnames__lt=RARE_OCCURRENCES_THRESHOLD)
        .order_by('distinct_hostnames')
        )
    
    data = []
    for query in queries:
        q = get_object_or_404(Query, pk=query['snapshot__query__id'])
        endpoints = Endpoint.objects.filter(snapshot__query=q).values('hostname').distinct()

        data.append({
            'id': query['snapshot__query__id'],
            'name': query['snapshot__query__name'],
            'confidence': query['snapshot__query__confidence'],
            'relevance': query['snapshot__query__relevance'],
            'description': query['snapshot__query__description'],
            'query': query['snapshot__query__query'],
            'distinct_hostnames': query['distinct_hostnames'],
            'endpoints': [endpoint['hostname'] for endpoint in endpoints]
            })        

    context = {
        'queries': data
        }
    
    return render(request, 'rare_occurrences.html', context)


@login_required
def zero_occurrence(request):
    queries_without_endpoints = Query.objects.filter(run_daily=True).annotate(
        endpoint_count=Count('snapshot__endpoint')).filter(endpoint_count=0)
    context = {
        'queries': queries_without_endpoints
        }
    return render(request, 'zero_occurrence.html', context)
