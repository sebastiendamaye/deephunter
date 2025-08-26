from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboards, name='dashboards'),
    path('listanalytics/', views.list_analytics, name='list_analytics'),
    path('<int:analytic_id>/trend/', views.trend, name='trend'),
    path('<int:analytic_id>/trend/<int:tab>/', views.trend, name='trend'),
    path('events/<int:analytic_id>/<str:eventdate>/<str:endpointname>/', views.events, name='events'),
    path('events/<int:analytic_id>/<str:eventdate>/', views.events, name='events'),
    path('events/<int:analytic_id>/', views.events, name='events'),
    path('threats/<str:connector>/<str:endpointname>/<str:date>/', views.threats, name='threats'),
    path('storyline/<str:storylineids>/<str:eventdate>/', views.storyline, name='storyline'),
    path('<int:analytic_id>/detail/', views.analyticdetail, name='analyticdetail'),
    path('saved_searches/', views.saved_searches, name='saved_searches'),
    path('saved_searches_table/', views.saved_searches_table, name='saved_searches_table'),
    path('saved_searches/add/', views.saved_search_form, name='saved_search_form'),
    path('saved_searches/<int:search_id>/change/', views.saved_search_form, name='saved_search_form'),
    path('saved_searches/<int:search_id>/delete/', views.delete_saved_search, name='delete_saved_search'),

    path('timeline', views.timeline, name='timeline'),

    path('tl_timeline/<str:hostname>/', views.tl_timeline, name='tl_timeline'),
    path('tl_host/<str:hostname>/', views.tl_host, name='tl_host'),
    path('tl_ad/<str:hostname>/', views.tl_ad, name='tl_ad'),
    path('tl_apps/<str:hostname>/', views.tl_apps, name='tl_apps'),

    path('<int:analytic_id>/regen/', views.regen, name='regen'),
    path('cancelregen/<str:taskid>/', views.cancelregen, name='cancelregen'),
    path('<int:analytic_id>/progress/', views.progress, name='progress'),
    path('<int:analytic_id>/deletestats/', views.deletestats, name='deletestats'),
    path('netview', views.netview, name='netview'),
    path('about', views.about, name='about'),
    path('managecampaigns', views.managecampaigns, name='managecampaigns'),
    path('regencampaign/<str:campaign_name>/', views.regencampaign, name='regencampaign'),
    path('regencampaignstatus/<str:campaign_name>/', views.regencampaignstatus, name='regencampaignstatus'),

    path('db_totalnumberanalytics/', views.db_totalnumberanalytics, name='db_totalnumberanalytics'),
    path('db_analyticsrunintodaycampaign/', views.db_analyticsrunintodaycampaign, name='db_analyticsrunintodaycampaign'),
    path('db_analyticsmatchingintodaycampaign/', views.db_analyticsmatchingintodaycampaign, name='db_analyticsmatchingintodaycampaign'),
    path('db_analyticstoreview/', views.db_analyticstoreview, name='db_analyticstoreview'),
    path('db_analyticspending/', views.db_analyticspending, name='db_analyticspending'),
    path('db_archivedanalytics/', views.db_archivedanalytics, name='db_archivedanalytics'),
    path('db_analyticsbystatus/', views.db_analyticsbystatus, name='db_analyticsbystatus'),
    path('db_analyticsbyconnector/', views.db_analyticsbyconnector, name='db_analyticsbyconnector'),
    path('db_analyticsbyuser/', views.db_analyticsbyuser, name='db_analyticsbyuser'),
    path('db_runningtasks/', views.db_runningtasks, name='db_runningtasks'),
    path('db_highestweightedscoretoday/', views.db_highestweightedscoretoday, name='db_highestweightedscoretoday'),
    path('db_analyticswitherrors/', views.db_analyticswitherrors, name='db_analyticswitherrors'),
    path('db_topendpointdistinctanalytics/', views.db_top_endpoint_distinct_analytics, name='db_top_endpoint_distinct_analytics'),

    path('edit_description_initial/<int:analytic_id>/', views.edit_description_initial, name='edit_description_initial'),
    path('edit_description_form/<int:analytic_id>/', views.edit_description_form, name='edit_description_form'),
    path('edit_description_submit/<int:analytic_id>/', views.edit_description_submit, name='edit_description_submit'),

    path('edit_notes_initial/<int:analytic_id>/', views.edit_notes_initial, name='edit_notes_initial'),
    path('edit_notes_form/<int:analytic_id>/', views.edit_notes_form, name='edit_notes_form'),
    path('edit_notes_submit/<int:analytic_id>/', views.edit_notes_submit, name='edit_notes_submit'),

    path('edit_query_initial/<int:analytic_id>/', views.edit_query_initial, name='edit_query_initial'),
    path('edit_query_form/<int:analytic_id>/', views.edit_query_form, name='edit_query_form'),
    path('edit_query_submit/<int:analytic_id>/', views.edit_query_submit, name='edit_query_submit'),
    
    path('statusbutton/<int:analytic_id>/', views.status_button, name='status_button'),
    path('changestatus/<int:analytic_id>/<str:updated_status>/', views.change_status, name='change_status'),
    path('deleteanalytic/<int:analytic_id>/', views.delete_analytic, name='delete_analytic'),
    path('rundailycheckbox/<int:analytic_id>/', views.rundailycheckbox, name='rundailycheckbox'),

    path('review_page/<int:analytic_id>/', views.review_page, name='review_page'),
    path('submit_review/<int:analytic_id>/', views.submit_review, name='submit_review'),
    path('reviews_table/<int:analytic_id>/', views.reviews_table, name='reviews_table'),

    path('get_notifications/', views.get_notifications, name='get_notifications'),

]
