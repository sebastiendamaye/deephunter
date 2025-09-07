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
    analytics = Analytic.objects.exclude(status='ARCH')    
    
    code = f"""<h3>Total number of analytics</h3>
        <p class="num"><a href="/qm/listanalytics/">{analytics.count()}</a></p>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticsrunintodaycampaign(request):
    campaign = get_object_or_404(Campaign, name='daily_cron_{}'.format(datetime.today().strftime('%Y-%m-%d')))
    
    code = f"""<h3>Analytics run in today's campaign</h3>
        <p class="num"><a href="/qm/listanalytics/?run_daily=1">{campaign.nb_queries}</p>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
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
        <p class="num"><a href="/reports/endpoints/">{highestweightedscore['total_weighted_score']}</p>
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
        <p class="num"><a href="/reports/highest_weighted_score/">{highest_score}</p>
        """
    return HttpResponse(code)


@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticstoreview(request):
    analytics = Analytic.objects.filter(status='REVIEW')
    
    code = f"""<h3>Analytics to review</h3>
        <p class="num"><a href="/qm/listanalytics/?statuses=REVIEW">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_analyticspending(request):
    analytics = Analytic.objects.filter(status='PENDING')
    
    code = f"""<h3>Analytics pending</h3>
        <p class="num"><a href="/qm/listanalytics/?statuses=PENDING">{analytics.count()}</p>
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
        <p class="num"><a href="/reports/query_error">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_archivedanalytics(request):
    analytics = Analytic.objects.filter(status='ARCH')
    
    code = f"""<h3>Archived analytics</h3>
        <p class="num"><a href="/admin/qm/analytic/?status__exact=ARCH">{analytics.count()}</p>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_tasksstatus', raise_exception=True)
def db_runningtasks(request):
    tasks = TasksStatus.objects.all()
    
    code = f"""<h3>Running tasks</h3>
        <p class="num"><a href="/admin/qm/tasksstatus/">{tasks.count()}</p>
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
        <p class="num"><a href="/reports/endpoints_most_analytics">{top_endpoints.first()['analytics_count']}</p>
        """
    return HttpResponse(code)

@login_required
@permission_required('qm.view_analytic', raise_exception=True)
def db_auto_disabled_analytics(request):
    analytics = Analytic.objects.filter(run_daily=0, maxhosts_count__gt=1).exclude(status='ARCH')
    
    code = f"""<h3>Auto-disabled analytics</h3>
        <p class="num"><a href="/qm/listanalytics/?run_daily=0&maxhosts=1">{analytics.count()}</p>
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