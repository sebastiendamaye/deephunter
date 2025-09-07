from django.urls import path
from . import views

urlpatterns = [
    path('connectorconf/', views.connector_conf, name='connector_conf_view'),
    path('selected-connector-settings/<int:connector_id>/', views.selected_connector_settings, name='selected_connector_settings_view'),
]
