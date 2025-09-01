from django.contrib import admin
from .models import Repo, RepoAnalytic

class RepoAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'is_private', 'token', 'get_nb_analytics', 'get_nb_analytics_valid', 'get_nb_analytics_errors', 'last_check_date', 'last_import_date')
    list_filter = ['last_check_date', 'last_import_date', 'is_private']
    search_fields = ['name', 'url']

    @admin.display(description='nb_analytics')
    def get_nb_analytics(self, obj):
        return obj.repoanalytic_set.count()

    @admin.display(description='nb_analytics_valid')
    def get_nb_analytics_valid(self, obj):
        return obj.repoanalytic_set.filter(is_valid=True).count()

    @admin.display(description='nb_analytics_errors')
    def get_nb_analytics_errors(self, obj):
        return obj.repoanalytic_set.filter(is_valid=False).count()


class RepoAnalyticAdmin(admin.ModelAdmin):
    list_display = ('repo', 'name', 'report', 'is_valid', 'url')
    list_filter = ['is_valid']
    search_fields = ['name']

admin.site.register(Repo, RepoAdmin)
admin.site.register(RepoAnalytic, RepoAnalyticAdmin)
