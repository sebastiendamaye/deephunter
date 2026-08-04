"""
URL routing for the DeepHunter REST API (mounted at /api/ by the project URLconf).

Authentication (django-rest-knox):
  Tokens are issued out-of-band with the `create_api_token` management command
  (local username/password login is intentionally not supported, since users
  authenticate through an external provider such as PingID and have no local
  password). Send the token as `Authorization: Token <token>`.
  POST /api/auth/logout/   Invalidate the token used for the request
  POST /api/auth/logoutall/ Invalidate all of the user's tokens

Analytics:
  GET  /api/analytics/           List analytics
  POST /api/analytics/           Create an analytic
  GET  /api/analytics/<id>/      Retrieve an analytic

Tags:
  GET  /api/tags/                List tags
  POST /api/tags/                Create a tag

Reference data (read-only, for discovering valid natural-key values):
  /api/ref/connectors/  /api/ref/categories/  /api/ref/tags/
  /api/ref/mitre-techniques/  /api/ref/threats/  /api/ref/actors/
  /api/ref/target-os/  /api/ref/vulnerabilities/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from knox import views as knox_views

from . import api


router = DefaultRouter()
router.register(r'ref/connectors', api.ConnectorRefViewSet, basename='ref-connector')
router.register(r'ref/categories', api.CategoryRefViewSet, basename='ref-category')
router.register(r'ref/tags', api.TagRefViewSet, basename='ref-tag')
router.register(r'ref/mitre-techniques', api.MitreTechniqueRefViewSet, basename='ref-mitre-technique')
router.register(r'ref/threats', api.ThreatNameRefViewSet, basename='ref-threat')
router.register(r'ref/actors', api.ThreatActorRefViewSet, basename='ref-actor')
router.register(r'ref/target-os', api.TargetOsRefViewSet, basename='ref-target-os')
router.register(r'ref/vulnerabilities', api.VulnerabilityRefViewSet, basename='ref-vulnerability')

urlpatterns = [
    # Authentication (Knox). Tokens are minted out-of-band via the
    # `create_api_token` management command; there is no password login endpoint.
    path('auth/logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('auth/logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),

    # Analytics
    path('analytics/', api.AnalyticListCreateView.as_view(), name='api_analytic_list_create'),
    path('analytics/<int:pk>/', api.AnalyticRetrieveView.as_view(), name='api_analytic_detail'),

    # Tags (list + create). Reference-only listing also lives at /api/ref/tags/;
    # this endpoint additionally supports POST to create a missing tag.
    path('tags/', api.TagListCreateView.as_view(), name='api_tag_list_create'),

    # Reference data
    path('', include(router.urls)),
]
