from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from . import views

admin.site.login_template = 'custom_admin/login.html'

favicon_view = RedirectView.as_view(url='/static/favicon.ico', permanent=True)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('logout/', views.user_logout, name='user_logout'),
    path('sso/', views.sso, name='sso'),
    path('authorize/', views.authorize, name='authorize'),
    re_path(r'^favicon\.ico$', favicon_view),
    path('', include('qm.urls')),
    path('qm/', include('qm.urls')),
    path('extensions/', include('extensions.urls')),
    path('reports/', include('reports.urls')),
    path('connectors/', include('connectors.urls')),
    path('repos/', include('repos.urls')),
]
