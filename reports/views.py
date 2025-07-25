from django.conf import settings
import json
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta
from qm.models import Analytic, Snapshot, Campaign, MitreTactic, MitreTechnique, Endpoint, Connector

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module


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
    
    connectors = Connector.objects.filter(visible_in_analytics=True)
    
    # initialize connector stats with empty lists
    connector_stats = {}
    for connector in connectors:
        connector_stats[connector.name] = []

    for i in reversed(range(DB_DATA_RETENTION)):
        #d=datetime.combine(datetime.today(), datetime.min.time()) - timedelta(days=i)
        d=datetime.today() - timedelta(days=i)
        
        try:
            campaign = get_object_or_404(Campaign, name=f"daily_cron_{d.strftime('%Y-%m-%d')}")
            difference = campaign.date_end - campaign.date_start
            dur = divmod(difference.days * seconds_in_day + difference.seconds, 60)
            duration = round(dur[0]+dur[1]*5/3/100, 1)
            count_endpoints_total = Endpoint.objects.filter(snapshot__campaign=campaign).count()
            
            # Recursily count endpoints per connector
            for connector in connectors:
                connector_stats[connector.name].append({
                    'date': d,
                    'count': Snapshot.objects.filter(
                        campaign=campaign,
                        analytic__connector=connector
                        ).count()
                    })

            stats.append({
                'date':d,
                'count_analytics':campaign.nb_queries,
                'duration':duration,
                'count_endpoints_total':count_endpoints_total,
                })
        except:
            stats.append({
                'date':d,
                'count_analytics':0,
                'duration':0,
                'count_endpoints_total':0
                })
    
    context = {
        'stats': stats,
        'connector_stats': connector_stats,
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
        score = Analytic.objects.filter(mitre_techniques=technique).count()
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
            numanalytics = Analytic.objects.filter(
                Q(mitre_techniques__mitre_id = technique.mitre_id)
                | Q(mitre_techniques__mitre_technique__mitre_id = technique.mitre_id)
            ).distinct().count()
            tmp.append({
                'mitre_id': technique.mitre_id,
                'name': technique.name,
                'numanalytics': numanalytics
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
        ).values('hostname', 'site').annotate(total=Sum('snapshot__analytic__weighted_relevance')).order_by('-total')[:20]
    data = []
    for endpoint in endpoints:
        hostname = endpoint['hostname']
        site = endpoint['site']
        analytics = Endpoint.objects.filter(
            snapshot__date=datetime.today()-timedelta(days=1),
            hostname=hostname
            ).order_by('-snapshot__analytic__weighted_relevance')
        
        qdata = []
        for analytic in analytics:
            
            startdate=(datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
            xdrlink = all_connectors.get(analytic.snapshot.analytic.connector.name).get_redirect_analytic_link(analytic.snapshot.analytic, date=startdate, endpoint_name=hostname)

            qdata.append({
                "analyticid":analytic.snapshot.analytic.id,
                "name":analytic.snapshot.analytic.name,
                "connector":analytic.snapshot.analytic.connector.name,
                "status":analytic.snapshot.analytic.status,
                "confidence":analytic.snapshot.analytic.confidence,
                "relevance":analytic.snapshot.analytic.relevance,
                "xdrlink":xdrlink
                })
        
        data.append({
            "hostname":hostname,
            "site":site,
            "total":endpoint['total'],
            "analytics":qdata
            })
    context = {
        'endpoints': data
        }
    
    return render(request, 'endpoints.html', context)


@login_required
def missing_mitre(request):
    # Number of analytics with unmapped MITRE techniques
    q_unmapped = Analytic.objects.filter(mitre_techniques=None)
    q_unmapped_count = q_unmapped.count()

    # Number of analytics with MITRE techniques mapped
    q_mapped_count = Analytic.objects.filter(~Q(mitre_techniques=None)).count()

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
    analytics = []
    
    for snapshot in snapshots:
        analytic_snapshots = Snapshot.objects.filter(analytic=snapshot.analytic, date__gt=datetime.today()-timedelta(days=20)).order_by('date')
        analytics.append({
                'id': snapshot.analytic.id,
                'name': snapshot.analytic.name,
                'connector': snapshot.analytic.connector.name,
                'runtime': snapshot.runtime,
                'status': snapshot.analytic.status,
                'sparkline': [analytic_snapshot.runtime for analytic_snapshot in analytic_snapshots]
            })
    
    context = {
        'analytics': analytics
        }
    
    return render(request, 'perfs.html', context)

@login_required
def query_error(request):
    analytics = Analytic.objects.filter(query_error = True)
    context = {
        'analytics': analytics
        }
    
    return render(request, 'query_error.html', context)

@login_required
def rare_occurrences(request):
    analytics = (
        Endpoint.objects
        .values('snapshot__analytic__id', 'snapshot__analytic__name', 'snapshot__analytic__connector__name', 'snapshot__analytic__status', 'snapshot__analytic__confidence', 'snapshot__analytic__relevance', 'snapshot__analytic__description', 'snapshot__analytic__query')
        .annotate(distinct_hostnames=Count('hostname', distinct=True))
        .filter(distinct_hostnames__lt=RARE_OCCURRENCES_THRESHOLD)
        .order_by('distinct_hostnames')
        )
    
    data = []
    for analytic in analytics:
        q = get_object_or_404(Analytic, pk=analytic['snapshot__analytic__id'])
        endpoints = Endpoint.objects.filter(snapshot__analytic=q).values('hostname').distinct()

        data.append({
            'id': analytic['snapshot__analytic__id'],
            'name': analytic['snapshot__analytic__name'],
            'connector': analytic['snapshot__analytic__connector__name'],
            'status': analytic['snapshot__analytic__status'],
            'confidence': analytic['snapshot__analytic__confidence'],
            'relevance': analytic['snapshot__analytic__relevance'],
            'description': analytic['snapshot__analytic__description'],
            'query': analytic['snapshot__analytic__query'],
            'distinct_hostnames': analytic['distinct_hostnames'],
            'endpoints': [endpoint['hostname'] for endpoint in endpoints]
            })        

    context = {
        'analytics': data
        }
    
    return render(request, 'rare_occurrences.html', context)


@login_required
def zero_occurrence(request):
    analytics_without_endpoints = Analytic.objects.filter(run_daily=True).annotate(
        endpoint_count=Count('snapshot__endpoint')).filter(endpoint_count=0)
    context = {
        'analytics': analytics_without_endpoints
        }
    return render(request, 'zero_occurrence.html', context)
