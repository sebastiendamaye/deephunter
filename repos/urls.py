from django.urls import path, re_path
from . import views

urlpatterns = [
    path('listrepos/', views.list_repos, name='list_repos'),
    path('syncreposelectanalytics/<int:repo_id>/', views.sync_repo_select_analytics, name='sync_repo_select_analytics'),
    path('syncrepo/<int:repo_id>/<str:mode>/', views.sync_repo, name='sync_repo'),
    path('deleterepo/<int:repo_id>/', views.delete_repo, name='delete_repo'),
    path('addrepo/', views.add_repo, name='add_repo'),
    path('editrepo/<int:repo_id>/', views.edit_repo, name='edit_repo'),
    path('deleterepo/<int:repo_id>/', views.delete_repo, name='delete_repo'),
    path('preview/<str:url>/', views.preview, name='preview'),
]
