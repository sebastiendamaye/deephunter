from django.contrib import admin
from .models import Country, TargetOs, Vulnerability, MitreTactic, MitreTechnique, ThreatName, ThreatActor, Query, Snapshot, Campaign, Endpoint, Tag, CeleryStatus, Category
from connectors.models import Connector
from django.contrib.admin.models import LogEntry
from simple_history.admin import SimpleHistoryAdmin
from django.conf import settings

admin.site.site_title = 'DeepHunter_'
admin.site.site_header = 'DeepHunter_'
admin.site.index_title = 'DeepHunter_'

CUSTOM_FIELDS = settings.CUSTOM_FIELDS

class QueryHistoryAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'update_date', 'created_by', 'pub_status', 'category', 'confidence', 'relevance', 'run_daily', 'run_daily_lock', 'star_rule', 'dynamic_query', 'query_error', 'maxhosts_count', 'connector', 'query')
    list_filter = ['pub_status', 'created_by', 'category', 'confidence', 'relevance', 'run_daily', 'run_daily_lock', 'star_rule', 'maxhosts_count', 'dynamic_query', 'query_error', 'mitre_techniques', 'mitre_techniques__mitre_tactic', 'threats__name', 'actors__name', 'target_os', 'tags__name', 'connector']
    search_fields = ['name', 'description', 'notes', 'emulation_validation']
    filter_horizontal = ('mitre_techniques', 'threats', 'actors', 'target_os', 'vulnerabilities', 'tags')
    history_list_display = ['query', 'columns']
    exclude = ('query_error', 'query_error_message')
    save_as = True

    # Only show connectors that are flagged for TH analytics
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "connector":
            kwargs["queryset"] = Connector.objects.filter(visible_in_analytics=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change): 
        if not change:
            # If the object is being created, set the created_by field to the current user
            obj.created_by = request.user
        return super().save_model(request, obj, form, change)

class SnapshotAdmin(admin.ModelAdmin):
    list_display = ('get_campaign', 'query', 'date', 'runtime', 'hits_count', 'hits_endpoints',)
    
    if CUSTOM_FIELDS['c1']:
        list_display += ('get_hits_c1',)
        c1_description = CUSTOM_FIELDS['c1']['description']
    else:
        c1_description = ''
    
    if CUSTOM_FIELDS['c2']:
        list_display += ('get_hits_c2',)
        c2_description = CUSTOM_FIELDS['c2']['description']
    else:
        c2_description = ''
    
    if CUSTOM_FIELDS['c3']:
        list_display += ('get_hits_c3',)
        c3_description = CUSTOM_FIELDS['c3']['description']
    else:
        c3_description = ''
    list_display += ('zscore_count', 'zscore_endpoints', 'anomaly_alert_count', 'anomaly_alert_endpoints',)
    list_filter = ['campaign__name', 'query', 'date', 'anomaly_alert_count', 'anomaly_alert_endpoints']
    
    @admin.display(description='campaign')
    def get_campaign(self, obj):
        return obj.campaign
    
    @admin.display(description=c1_description)
    def get_hits_c1(self, obj):
        return obj.hits_c1
        
    @admin.display(description=c2_description)
    def get_hits_c2(self, obj):
        return obj.hits_c2
    
    @admin.display(description=c3_description)
    def get_hits_c3(self, obj):
        return obj.hits_c3
    
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'date_start', 'date_end', 'nb_queries')
    list_filter = ['date_start', 'date_end', 'nb_queries']
    search_fields = ['name', 'description']

class MitreTacticAdmin(admin.ModelAdmin):
    list_display = ('mitre_id', 'name', 'description')

class MitreTechniqueAdmin(admin.ModelAdmin):
    list_display = ('mitre_id', 'name', 'is_subtechnique', 'mitre_technique', 'description')
    list_filter = ['is_subtechnique', 'mitre_tactic']
    filter_horizontal = ('mitre_tactic',)
    search_fields = ['mitre_id', 'name', 'description']

class VulnerabilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_score', 'description', 'references')
    list_filter = ['base_score']
    search_fields = ['name', 'description']

class ThreatNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'aka_name', 'references')
    search_fields = ['name', 'aka_name']

class ThreatActorAdmin(admin.ModelAdmin):
    list_display = ('name', 'aka_name', 'source_country', 'references')
    list_filter = ['source_country']
    search_fields = ['name', 'aka_name']

class EndpointAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'site', 'get_query', 'get_confidence', 'get_relevance', 'get_date', 'storylineid')
    list_filter = ['snapshot__date', 'site', 'snapshot__query__confidence', 'snapshot__query__relevance', 'snapshot__query__name']
    search_fields = ['hostname', 'snapshot__query__name', 'storylineid']

    @admin.display(description='query')
    def get_query(self, obj):
        return obj.snapshot.query
    
    @admin.display(description='confidence')
    def get_confidence(self, obj):
        return obj.snapshot.query.confidence
    
    @admin.display(description='relevance')
    def get_relevance(self, obj):
        return obj.snapshot.query.relevance
    
    @admin.display(description='date')
    def get_date(self, obj):
        return obj.snapshot.date

class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ['user', 'content_type', 'action_flag']

class CeleryStatusAdmin(admin.ModelAdmin):
    list_display = ('query', 'date', 'progress')

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'description')

admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Tag)
admin.site.register(Country)
admin.site.register(TargetOs)
admin.site.register(Vulnerability, VulnerabilityAdmin)
admin.site.register(MitreTactic, MitreTacticAdmin)
admin.site.register(MitreTechnique, MitreTechniqueAdmin)
admin.site.register(ThreatName, ThreatNameAdmin)
admin.site.register(ThreatActor, ThreatActorAdmin)
admin.site.register(Query, QueryHistoryAdmin)
admin.site.register(Snapshot, SnapshotAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(Endpoint, EndpointAdmin)
admin.site.register(CeleryStatus, CeleryStatusAdmin)
admin.site.register(Category, CategoryAdmin)
