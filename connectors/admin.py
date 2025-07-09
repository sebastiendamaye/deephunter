from django.contrib import admin
from .models import Connector, ConnectorConf
from django.conf import settings

class ConnectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'enabled', 'visible_in_analytics')
    list_filter = ['name', 'description']
    search_fields = ['name', 'description']

class ConnectorConfAdmin(admin.ModelAdmin):
    list_display = ('connector', 'key', 'value', 'description')
    list_filter = ['connector', 'key']
    search_fields = ['key', 'value', 'description']

admin.site.register(Connector, ConnectorAdmin)
admin.site.register(ConnectorConf, ConnectorConfAdmin)
