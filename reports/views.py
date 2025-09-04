from django.conf import settings
import json
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from qm.models import Analytic, Snapshot, Campaign, MitreTactic, MitreTechnique, Endpoint, Connector
from notifications.utils import add_debug_notification

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

ANALYTICS_PER_PAGE = settings.ANALYTICS_PER_PAGE

@login_required
def campaigns_stats(request):
    stats = []
    seconds_in_day = 24 * 60 * 60
    
    connectors = Connector.objects.filter(domain="analytics")
    
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
            ).exclude(status='ARCH').distinct().count()
            tmp.append({
                'id': technique.id,
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

    # list of campaigns
    campaigns = Campaign.objects.filter(name__startswith='daily_cron_').order_by('-name')

    if request.method == 'POST':
        # if a campaign is selected, filter endpoints by that campaign
        selected_campaign_id = request.POST.get('campaign')
    else:
        # default to the most recent campaign
        selected_campaign = campaigns.first()
        selected_campaign_id = selected_campaign.id

    campaign = get_object_or_404(Campaign, id=selected_campaign_id)

    # select TOP 20 endpoints for today's campaign
    endpoints = Endpoint.objects.filter(
        snapshot__campaign=campaign
        ).values('hostname', 'site').annotate(total=Sum('snapshot__analytic__weighted_relevance')).order_by('-total')[:300]
    data = []
    for endpoint in endpoints:
        hostname = endpoint['hostname']
        site = endpoint['site']
        analytics = Endpoint.objects.filter(
            snapshot__campaign=campaign,
            hostname=hostname
            ).order_by('-snapshot__analytic__weighted_relevance')
        
        qdata = []
        for analytic in analytics:
            
            startdate=analytic.snapshot.date.strftime('%Y-%m-%d')
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

    paginator = Paginator(data, ANALYTICS_PER_PAGE)
    page_number = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page_number)

    context = {
        'campaigns': campaigns,
        'selected_campaign_id': selected_campaign_id,
        'endpoints': page_obj
        }
    
    return render(request, 'endpoints.html', context)

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

    paginator = Paginator(analytics, ANALYTICS_PER_PAGE)
    page_number = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page_number)

    context = {
        'analytics': page_obj
        }
    
    return render(request, 'perfs.html', context)

@login_required
def query_error(request):
    context = {}
    return render(request, 'query_error.html', context)

@login_required
def query_error_table(request):
    analytics_with_errors = Analytic.objects.filter(query_error = True).exclude(status='ARCH').order_by('-query_error_date')
    include_info = request.GET.get('include_info', 'off') == 'on'  # Get checkbox value
    
    analytics = []
    for analytic in analytics_with_errors:
        error_is_info = all_connectors.get(analytic.connector.name).error_is_info(analytic.query_error_message)
        if (not error_is_info) or (error_is_info and include_info):
            analytics.append({
                'id': analytic.id,
                'name': analytic.name,
                'description': analytic.description,
                'query': analytic.query,
                'status': analytic.status,
                'maxhosts_count': analytic.maxhosts_count,
                'connector_name': analytic.connector.name,
                'run_daily': analytic.run_daily,
                'error': analytic.query_error,
                'error_is_info': error_is_info,
                'query_error_message': analytic.query_error_message,
                'query_error_date': analytic.query_error_date,
            })

    paginator = Paginator(analytics, ANALYTICS_PER_PAGE)
    page_number = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page_number)

    context = {
        'analytics': page_obj
        }
    
    return render(request, 'partials/query_error_table.html', context)


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

    paginator = Paginator(data, ANALYTICS_PER_PAGE)
    page_number = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page_number)

    context = {
        'analytics': page_obj
        }
    
    return render(request, 'rare_occurrences.html', context)


@login_required
def endpoints_most_analytics(request):
    # Limited to first 300 endpoints with the most analytics
    top_endpoints = (
        Endpoint.objects
        .values('hostname', 'site')
        .annotate(analytics_count=Count('snapshot__analytic', distinct=True))
        .order_by('-analytics_count')[:300]
    )

    paginator = Paginator(top_endpoints, ANALYTICS_PER_PAGE)
    page_number = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page_number)

    context = {
        'top_endpoints': page_obj,
    }
    return render(request, 'endpoints_most_analytics.html', context)

@login_required
def upcoming_analytic_reviews(request):
    analytics = (
        Analytic.objects
        .filter(next_review_date__isnull=False)
        .exclude(status='ARCH')
        .values('next_review_date')
        .annotate(count=Count('id'))
        .order_by('next_review_date')
    )
    context = {'analytics': analytics}
    return render(request, 'upcoming_analytic_reviews.html', context)

@login_required
def highest_weighted_score(request):
    results = []
    highest_score = 0
    campaigns = Campaign.objects.filter(name__startswith='daily_cron_').order_by('date_start')
    for campaign in campaigns:
        qs = Endpoint.objects.filter(
            snapshot__campaign=campaign
        ).values('hostname').annotate(
            total_weighted_score=Sum(F('snapshot__analytic__weighted_relevance'))
        ).order_by('-total_weighted_score')
        highestweightedscore = qs.first()
        if highestweightedscore:
            highest_weighted_relevance = highestweightedscore['total_weighted_score']
            hostname = highestweightedscore['hostname']
        else:
            highest_weighted_relevance = 0
            hostname = ''
        results.append({
            "date": campaign.date_start,
            "hostname": hostname,
            "highest_weighted_relevance": highest_weighted_relevance,
            "color": "#4661EE"  # Default color (light blue)
            })

    # Find the item with the highest score and give them the red color
    max_score = max(int(item["highest_weighted_relevance"]) for item in results)
    for item in results:
        if int(item["highest_weighted_relevance"]) == max_score:
            item["color"] = "#FF6961"  # Red color for the highest score

    context = {
        'results': results,
    }
    return render(request, 'highest_weighted_score.html', context)
