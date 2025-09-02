from django.contrib import admin
from .models import (Country, TargetOs, Vulnerability, MitreTactic, MitreTechnique, ThreatName,  
    ThreatActor, Analytic, Snapshot, Campaign, Endpoint, Tag, TasksStatus, Category, Review, SavedSearch)
from connectors.models import Connector
from django.contrib.admin.models import LogEntry
from simple_history.admin import SimpleHistoryAdmin
from django.conf import settings
from datetime import datetime, timedelta
from django.contrib import messages

admin.site.site_title = 'DeepHunter_'
admin.site.site_header = 'DeepHunter_'
admin.site.index_title = 'DeepHunter_'

class MaxHostsCountFilter(admin.SimpleListFilter):
    title = 'Max Hosts Count'
    parameter_name = 'maxhosts_count'

    def lookups(self, request, model_admin):
        return [
            ('zero', 'Equal to 0'),
            ('greater_than_zero', 'Greater than 0'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'zero':
            return queryset.filter(maxhosts_count=0)
        if value == 'greater_than_zero':
            return queryset.filter(maxhosts_count__gt=0)
        return queryset

class HitsLastCampaignFilter(admin.SimpleListFilter):
    title = 'Hits for last campaign'
    parameter_name = 'hits'

    def lookups(self, request, model_admin):
        return [
            ('1', 'yes'),
            ('0', 'no'),
        ]

    def queryset(self, request, queryset):
        value = self.value()

        # Get yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_date = yesterday.date()  # Get the date part

        if value == '1':
            return queryset.filter(
                snapshot__hits_count__gt=0,
                snapshot__date=yesterday_date
            ).distinct()
        if value == '0':
            return queryset.filter(
                snapshot__hits_count=0,
                snapshot__date=yesterday_date
            ).distinct()
        return queryset

class AlreadySeenFilter(admin.SimpleListFilter):
    title = 'Already seen'
    parameter_name = 'alreadyseen'

    def lookups(self, request, model_admin):
        return [
            ('1', 'yes'),
            ('0', 'no'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == '1':
            return queryset.filter(last_time_seen__isnull=False)
        if value == '0':
            return queryset.filter(last_time_seen__isnull=True)
        return queryset

class NotStatusFilter(admin.SimpleListFilter):
    title = 'Exclude Status'
    parameter_name = 'not_status'

    def lookups(self, request, model_admin):
        return [
            ('DRAFT', 'Not Draft'),
            ('PUB', 'Not Published'),
            ('REVIEW', 'Not to be reviewed'),
            ('PENDING', 'Not Pending'),
            ('ARCH', 'Not Archived'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.exclude(status=self.value())
        return queryset
    
class AnalyticAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'update_date', 'created_by', 'status', 'category', 'confidence', 'relevance', 'run_daily',
                    'run_daily_lock', 'create_rule', 'dynamic_query', 'query_error', 'query_error_date', 'maxhosts_count',
                    'connector', 'query', 'last_time_seen', 'repo')
    list_filter = ['repo', 'status', NotStatusFilter, 'created_by', 'category', 'confidence', 'relevance', 'run_daily',
                   'run_daily_lock', 'create_rule', MaxHostsCountFilter, 'dynamic_query', 'query_error', 'query_error_date',
                   'last_time_seen', 'mitre_techniques', 'mitre_techniques__mitre_tactic', 'threats__name', 'actors__name',
                   'actors__source_country', 'target_os', 'tags__name', 'connector', 'vulnerabilities',
                   HitsLastCampaignFilter, AlreadySeenFilter]
    search_fields = ['name', 'description', 'notes', 'emulation_validation']
    filter_horizontal = ('mitre_techniques', 'threats', 'actors', 'target_os', 'vulnerabilities', 'tags')
    history_list_display = ['query']
    save_as = True
    actions = ['update_status_draft', 'update_status_pub', 'update_status_review', 'update_status_arch', 'update_status_pending']

    # When creating or updating analytics, only show connectors that are flagged for TH analytics
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "connector":
            kwargs["queryset"] = Connector.objects.filter(domain="analytics")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change): 
        if not change:
            # If the object is being created, set the created_by field to the current user
            obj.created_by = request.user
        return super().save_model(request, obj, form, change)

    def update_status_draft(self, request, queryset):
        updated_count = queryset.update(status='DRAFT')
        self.message_user(request, f"{updated_count} analytics updated to DRAFT status.", messages.SUCCESS)
    update_status_draft.short_description = "Mark selected entries as DRAFT."

    def update_status_pub(self, request, queryset):
        updated_count = queryset.update(status='PUB')
        self.message_user(request, f"{updated_count} analytics updated to PUB status.", messages.SUCCESS)
    update_status_pub.short_description = "Mark selected entries as PUB."

    def update_status_review(self, request, queryset):
        updated_count = queryset.update(status='REVIEW')
        self.message_user(request, f"{updated_count} analytics updated to REVIEW status.", messages.SUCCESS)
    update_status_review.short_description = "Mark selected entries as REVIEW."

    def update_status_arch(self, request, queryset):
        updated_count = queryset.update(status='ARCH')
        self.message_user(request, f"{updated_count} analytics updated to ARCH status.", messages.SUCCESS)
    update_status_arch.short_description = "Mark selected entries as ARCH."

    def update_status_pending(self, request, queryset):
        updated_count = queryset.update(status='PENDING')
        self.message_user(request, f"{updated_count} analytics updated to PENDING status.", messages.SUCCESS)
    update_status_pending.short_description = "Mark selected entries as PENDING."


class SnapshotAdmin(admin.ModelAdmin):
    list_display = ('get_campaign', 'analytic__name', 'analytic__connector__name', 'date', 'runtime', 'hits_count', 'hits_endpoints','zscore_count', 'zscore_endpoints', 'anomaly_alert_count', 'anomaly_alert_endpoints',)
    list_filter = ['campaign__name', 'analytic__connector__name', 'analytic__name', 'date', 'anomaly_alert_count', 'anomaly_alert_endpoints']
    
    @admin.display(description='campaign')
    def get_campaign(self, obj):
        return obj.campaign
    
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
    list_display = ('hostname', 'site', 'get_analytic_name', 'get_connector_name', 'get_confidence', 'get_relevance', 'get_date', 'storylineid')
    list_filter = ['snapshot__date', 'site', 'snapshot__analytic__connector__name', 'snapshot__analytic__confidence', 'snapshot__analytic__relevance', 'snapshot__analytic__name']
    search_fields = ['hostname', 'snapshot__analytic__name', 'storylineid']

    @admin.display(description='analytic')
    def get_analytic_name(self, obj):
        return obj.snapshot.analytic.name

    @admin.display(description='connector')
    def get_connector_name(self, obj):
        return obj.snapshot.analytic.connector.name

    @admin.display(description='confidence')
    def get_confidence(self, obj):
        return obj.snapshot.analytic.confidence
    
    @admin.display(description='relevance')
    def get_relevance(self, obj):
        return obj.snapshot.analytic.relevance
    
    @admin.display(description='date')
    def get_date(self, obj):
        return obj.snapshot.date

class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ['user', 'content_type', 'action_flag']

class TasksStatusAdmin(admin.ModelAdmin):
    list_display = ('taskname', 'taskid', 'date', 'progress')

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'description')

class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'search', 'is_public', 'is_locked', 'created_by', 'pub_date', 'update_date')
    search_fields = ['name', 'description']
    list_filter = ['is_public', 'is_locked', 'created_by', 'pub_date', 'update_date']

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set on creation
            obj.created_by = request.user
        obj.save()

admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Tag)
admin.site.register(Country)
admin.site.register(TargetOs)
admin.site.register(Vulnerability, VulnerabilityAdmin)
admin.site.register(MitreTactic, MitreTacticAdmin)
admin.site.register(MitreTechnique, MitreTechniqueAdmin)
admin.site.register(ThreatName, ThreatNameAdmin)
admin.site.register(ThreatActor, ThreatActorAdmin)
admin.site.register(Analytic, AnalyticAdmin)
admin.site.register(Review)
admin.site.register(Snapshot, SnapshotAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(Endpoint, EndpointAdmin)
admin.site.register(TasksStatus, TasksStatusAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(SavedSearch, SavedSearchAdmin)