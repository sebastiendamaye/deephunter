from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:analytic_id>/trend/', views.trend, name='trend'),
    path('events/<int:analytic_id>/<str:eventdate>/<str:endpointname>/', views.events, name='events'),
    path('events/<int:analytic_id>/<str:eventdate>/', views.events, name='events'),
    path('events/<int:analytic_id>/', views.events, name='events'),
    path('storyline/<str:storylineids>/<str:eventdate>/', views.storyline, name='storyline'),
    path('<int:analytic_id>/detail/', views.analyticdetail, name='analyticdetail'),
    path('debug', views.debug, name='debug'),
    path('timeline', views.timeline, name='timeline'),
    path('<int:analytic_id>/regen/', views.regen, name='regen'),
    path('cancelregen/<str:taskid>/', views.cancelregen, name='cancelregen'),
    path('<int:analytic_id>/progress/', views.progress, name='progress'),
    path('<int:analytic_id>/deletestats/', views.deletestats, name='deletestats'),
    path('netview', views.netview, name='netview'),
    path('about', views.about, name='about'),
    path('notifications', views.notifications, name='notifications'),
]
