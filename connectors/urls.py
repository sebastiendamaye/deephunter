from django.urls import path
from . import views

urlpatterns = [
    path('connectorconf/', views.connector_conf, name='connector_conf_view'),
]
