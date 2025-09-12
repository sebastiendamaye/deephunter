from django.urls import path
from . import views

urlpatterns = [
    path('connectorconf/', views.connector_conf, name='connector_conf'),
    path('selected-connector-settings/<int:connector_id>/', views.selected_connector_settings, name='selected_connector_settings'),
    path('toggle-connector/<int:connector_id>/', views.toggle_connector, name='toggle_connector'),
]
