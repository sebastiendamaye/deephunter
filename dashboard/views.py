from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, Sum, Count, F
from datetime import datetime, timedelta, timezone
from qm.models import Analytic, Campaign, Endpoint, TasksStatus
from django.http import HttpResponse


@login_required
def dashboards(request):
    context = {}
    return render(request, 'dashboards.html', context)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_totalnumberanalytics(request):
    sparkline = []
    for i in range(30, 0, -1):
        try:
            campaign = get_object_or_404(Campaign, name=f"daily_cron_{(datetime.now() - timedelta(days=i-1)).strftime('%Y-%m-%d')}")
            sparkline.append(campaign.nb_analytics)
        except:
            sparkline.append(0)

    created_since_last_month = sparkline[-1] - sparkline[0]
    context = {
        'analytics_count': Analytic.objects.exclude(status='ARCH').count(),
        'created_since_last_month': created_since_last_month,
        'sparkline': sparkline,
    }
    return render(request, 'db_total_number_analytics.html', context)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticsrunintodaycampaign(request):
    campaign_today = get_object_or_404(Campaign, name='daily_cron_{}'.format(datetime.today().strftime('%Y-%m-%d')))
    campaign_yesterday = get_object_or_404(Campaign, name='daily_cron_{}'.format((datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')))
    delta = campaign_today.nb_queries - campaign_yesterday.nb_queries

    sparkline = []
    for i in range(30, 0, -1):
        try:
            campaign = get_object_or_404(Campaign, name=f"daily_cron_{(datetime.now() - timedelta(days=i-1)).strftime('%Y-%m-%d')}")
            sparkline.append(campaign.nb_queries)
        except:
            sparkline.append(0)

    context = {
        'campaign_today_nb_queries': campaign_today.nb_queries,
        'delta': delta,
        'sparkline': sparkline,
    }    
    return render(request, 'db_analyticsrunintodaycampaign.html', context)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticsmatchingintodaycampaign(request):

    sparkline = []
    for i in range(30, 0, -1):
        day = datetime.now() - timedelta(days=i)
        day_date = day.date()
        count = Analytic.objects.filter(
            snapshot__hits_count__gt=0,
            snapshot__date=day_date
        ).distinct().count()
        sparkline.append(count)

    context = {
        'sparkline': sparkline,
        'analytics_yesterday_count': sparkline[-1],
        'delta': sparkline[-1] - sparkline[-2] if len(sparkline) > 1 else 0,
    }
    return render(request, 'db_analyticsmatchingintodaycampaign.html', context)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_campaign_completion(request):

    campaign = get_object_or_404(Campaign, name='daily_cron_{}'.format(datetime.today().strftime('%Y-%m-%d')))
    analytics_run = Analytic.objects.filter(
        snapshot__campaign=campaign
    ).count()
    analytics_target = campaign.nb_queries

    code = "<h3>Campaign completion<br />(run/target)</h3>"
    if analytics_run == analytics_target:
        code += f"""<div class="num_green"><a href="/qm/managecampaigns">{analytics_run}/{analytics_target}</a></div>"""
    else:
        code += f"""<div class="num_red"><a href="/qm/managecampaigns">{analytics_run}/{analytics_target}</a></div>"""
    return HttpResponse(code)

@login_required
@permission_required('qm.view_endpoint', raise_exception=True)
def db_highestweightedscoretoday(request):

    campaign = get_object_or_404(Campaign, name='daily_cron_{}'.format(datetime.today().strftime('%Y-%m-%d')))

    qs = Endpoint.objects.filter(
        snapshot__campaign=campaign
    ).values('hostname').annotate(
        total_weighted_score=Sum(F('snapshot__analytic__weighted_relevance'))
    ).order_by('-total_weighted_score')

    # Get the highest score
    highestweightedscore = qs.first()
    
    code = f"""<h3>Endpoint with highest weighted relevance today</h3>
        <div class="num"><a href="/reports/endpoints/">{highestweightedscore['total_weighted_score']}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_endpoint', raise_exception=True)
def db_highest_weighted_score_all_campaigns(request):

    highest_score = 0
    campaigns = Campaign.objects.filter(name__startswith='daily_cron_')
    for campaign in campaigns:
        qs = Endpoint.objects.filter(
            snapshot__campaign=campaign
        ).values('hostname').annotate(
            total_weighted_score=Sum(F('snapshot__analytic__weighted_relevance'))
        ).order_by('-total_weighted_score')
        highestweightedscore = qs.first()
        if highestweightedscore:
            highest_weighted_relevance = highestweightedscore['total_weighted_score']
            if highest_weighted_relevance > highest_score:
                highest_score = highest_weighted_relevance

    code = f"""<h3>Enpoint with highest weighted relevance (all campaigns)</h3>
        <div class="num"><a href="/reports/highest_weighted_score/">{highest_score}</a></div>
        """
    return HttpResponse(code)


@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticstoreview(request):
    analytics = Analytic.objects.filter(status='REVIEW')
    
    code = f"""<h3>Analytics to review</h3>
        <div class="num"><a href="/qm/listanalytics/?statuses=REVIEW">{analytics.count()}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticspending(request):
    analytics = Analytic.objects.filter(status='PENDING')
    
    code = f"""<h3>Analytics pending</h3>
        <div class="num"><a href="/qm/listanalytics/?statuses=PENDING">{analytics.count()}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticswitherrors(request):
    analytics = Analytic.objects.filter(query_error=True).exclude(
        query_error_message__contains='"status":"FINISHED"').exclude(
        query_error_message__contains="'status': 'FINISHED'"
        ).exclude(status='ARCH')
    
    code = f"""<h3>Analytics with errors</h3>
        <div class="num"><a href="/reports/query_error">{analytics.count()}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_archivedanalytics(request):
    analytics = Analytic.objects.filter(status='ARCH')
    
    code = f"""<h3>Archived analytics</h3>
        <div class="num"><a href="/admin/qm/analytic/?status__exact=ARCH">{analytics.count()}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_tasksstatus', raise_exception=True)
def db_runningtasks(request):
    tasks = TasksStatus.objects.all()
    
    code = f"""<h3>Running tasks</h3>
        <div class="num"><a href="/config/running-tasks/">{tasks.count()}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_endpoint', raise_exception=True)
def db_top_endpoint_distinct_analytics(request):
    top_endpoints = (
        Endpoint.objects
        .values('hostname', 'site')
        .annotate(analytics_count=Count('snapshot__analytic', distinct=True))
        .order_by('-analytics_count')
    )
    
    code = f"""<h3>Most distinct analytics on single endpoint</h3>
        <div class="num"><a href="/reports/endpoints_most_analytics">{top_endpoints.first()['analytics_count']}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_auto_disabled_analytics(request):
    analytics = Analytic.objects.filter(run_daily=0, maxhosts_count__gt=1).exclude(status='ARCH')
    
    code = f"""<h3>Auto-disabled analytics</h3>
        <div class="num"><a href="/qm/listanalytics/?run_daily=0&maxhosts=1">{analytics.count()}</a></div>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticsbystatus(request):
    status_breakdown = Analytic.objects.values('status').exclude(status='ARCH').annotate(count=Count('id'))
    context = { 'status_breakdown': status_breakdown, }
    return render(request, 'db_analyticsbystatus.html', context)        

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticsbyconnector(request):
    connector_breakdown = Analytic.objects.values('connector__id', 'connector__name').exclude(status='ARCH').annotate(count=Count('id'))
    context = { 'connector_breakdown': connector_breakdown, }
    return render(request, 'db_analyticsbyconnector.html', context)        

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticsbyuser(request):
    analytics_breakdown = Analytic.objects.values('created_by__id', 'created_by__username').exclude(status='ARCH').annotate(count=Count('id'))
    context = { 'analytics_breakdown': analytics_breakdown, }
    return render(request, 'db_analyticsbyuser.html', context)        

@login_required
@permission_required('qm.view_review', raise_exception=True)
def db_analytics_reviews_workload(request):
    analytics = (
        Analytic.objects
        .filter(next_review_date__isnull=False, next_review_date__lt=datetime.now()+timedelta(weeks=2))
        .exclude(status='ARCH')
        .values('next_review_date')
        .annotate(count=Count('id'))
        .order_by('next_review_date')
    )
    context = {'analytics': analytics}
    return render(request, 'db_analytics_reviews_workload.html', context)