from django.urls import path, re_path
from . import views

urlpatterns = [
    path('listrepos/', views.list_repos, name='list_repos'),
    path('importreposelectanalytics/<int:repo_id>/', views.import_repo_select_analytics, name='import_repo_select_analytics'),
    path('importrepo/<int:repo_id>/<str:mode>/', views.import_repo, name='import_repo'),
    path('deleterepo/<int:repo_id>/', views.delete_repo, name='delete_repo'),
    path('addrepo/', views.add_repo, name='add_repo'),
    path('editrepo/<int:repo_id>/', views.edit_repo, name='edit_repo'),
    path('deleterepo/<int:repo_id>/', views.delete_repo, name='delete_repo'),
    path('preview/<str:url>/', views.preview, name='preview'),
    path('report/<int:repo_id>/', views.report, name='report'),
    path('cancel-import-repo/<str:taskid>/', views.cancel_import_repo, name='cancel_import_repo'),
    path('<int:repo_id>/progress-import-repo/', views.progress_import_repo, name='progress_import_repo'),
    path('<int:repo_id>/get-repo-import-info/', views.get_repo_import_info, name='get_repo_import_info'),
]
