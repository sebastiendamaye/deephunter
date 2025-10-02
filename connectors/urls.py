from django.urls import path
from . import views

urlpatterns = [
    path('connectorconf/', views.connector_conf, name='connector_conf'),
    path('selected-connector-settings/<int:connector_id>/', views.selected_connector_settings, name='selected_connector_settings'),
    path('toggle-connector-enabled/<int:connector_id>/', views.toggle_connector_enabled, name='toggle_connector_enabled'),
    path('toggle-connector-installed/<int:connector_id>/', views.toggle_connector_installed, name='toggle_connector_installed'),
    path('catalog/', views.catalog, name='catalog'),
    path('filter-catalog/', views.filter_catalog, name='filter_catalog'),
]
