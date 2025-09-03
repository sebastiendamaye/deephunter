from django.urls import path
from . import views

urlpatterns = [
    path('campaigns_stats/', views.campaigns_stats, name='campaigns_stats'),
    path('analytics_perfs/', views.analytics_perfs, name='analytics_perfs'),
    path('mitre/', views.mitre, name='mitre'),
    path('endpoints/', views.endpoints, name='endpoints'),
    path('query_error/', views.query_error, name='query_error'),
    path('query_error_table/', views.query_error_table, name='query_error_table'),
    path('rare_occurrences/', views.rare_occurrences, name='rare_occurrences'),
    path('endpoints_most_analytics/', views.endpoints_most_analytics, name='endpoints_most_analytics'),
    path('upcoming-analytic-reviews/', views.upcoming_analytic_reviews, name='upcoming_analytic_reviews'),
]
