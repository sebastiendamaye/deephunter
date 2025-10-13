from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboards, name='dashboards'),
    path('db_totalnumberanalytics/', views.db_totalnumberanalytics, name='db_totalnumberanalytics'),
    path('db_analyticsrunintodaycampaign/', views.db_analyticsrunintodaycampaign, name='db_analyticsrunintodaycampaign'),
    path('db_analyticsmatchingintodaycampaign/', views.db_analyticsmatchingintodaycampaign, name='db_analyticsmatchingintodaycampaign'),
    path('db_analyticstoreview/', views.db_analyticstoreview, name='db_analyticstoreview'),
    path('db_analyticspending/', views.db_analyticspending, name='db_analyticspending'),
    path('db_archivedanalytics/', views.db_archivedanalytics, name='db_archivedanalytics'),
    path('db_runningtasks/', views.db_runningtasks, name='db_runningtasks'),
    path('db_highestweightedscoretoday/', views.db_highestweightedscoretoday, name='db_highestweightedscoretoday'),
    path('db_highest-weighted-score-all-campaigns/', views.db_highest_weighted_score_all_campaigns, name='db_highest_weighted_score_all_campaigns'),
    path('db_analyticswitherrors/', views.db_analyticswitherrors, name='db_analyticswitherrors'),
    path('db_topendpointdistinctanalytics/', views.db_top_endpoint_distinct_analytics, name='db_top_endpoint_distinct_analytics'),
    path('db_auto-disabled-analytics/', views.db_auto_disabled_analytics, name='db_auto_disabled_analytics'),
    path('db_analyticsbystatus/', views.db_analyticsbystatus, name='db_analyticsbystatus'),
    path('db_analyticsbyconnector/', views.db_analyticsbyconnector, name='db_analyticsbyconnector'),
    path('db_analyticsbyuser/', views.db_analyticsbyuser, name='db_analyticsbyuser'),
    path('db_analytics-reviews-workload/', views.db_analytics_reviews_workload, name='db_analytics_reviews_workload'),
    path('db-campaign-completion/', views.db_campaign_completion, name='db_campaign_completion'),
]
