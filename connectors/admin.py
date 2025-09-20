from django.contrib import admin
from .models import Connector, ConnectorConf

class ConnectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'enabled', 'domain')
    list_filter = ['name', 'description', 'domain']
    search_fields = ['name', 'description']

class ConnectorConfAdmin(admin.ModelAdmin):
    list_display = ('connector', 'key', 'value', 'fieldtype', 'description')
    list_filter = ['connector', 'key', 'fieldtype']
    search_fields = ['key', 'value', 'description']

admin.site.register(Connector, ConnectorAdmin)
admin.site.register(ConnectorConf, ConnectorConfAdmin)
