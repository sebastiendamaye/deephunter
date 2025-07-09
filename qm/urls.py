from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:query_id>/trend/', views.trend, name='trend'),
    #path('<int:query_id>/pq/', views.pq, name='pq'),
    path('events/<int:query_id>/<str:eventdate>/<str:endpointname>/', views.events, name='events'),
    path('events/<int:query_id>/<str:eventdate>/', views.events, name='events'),
    path('events/<int:query_id>/', views.events, name='events'),
    path('storyline/<str:storylineids>/<str:eventdate>/', views.storyline, name='storyline'),
    path('<int:query_id>/detail/', views.querydetail, name='querydetail'),
    path('debug', views.debug, name='debug'),
    path('timeline', views.timeline, name='timeline'),
    path('<int:query_id>/regen/', views.regen, name='regen'),
    path('<int:query_id>/progress/', views.progress, name='progress'),
    path('<int:query_id>/deletestats/', views.deletestats, name='deletestats'),
    path('netview', views.netview, name='netview'),
    path('about', views.about, name='about'),
    path('notifications', views.notifications, name='notifications'),
]
