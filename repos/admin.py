from django.contrib import admin
from .models import Repo

class RepoAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'nb_analytics', 'nb_analytics_valid', 'nb_analytics_errors', 'last_check_date', 'last_sync_date')
    list_filter = ['last_check_date', 'last_sync_date']
    search_fields = ['name', 'url']

admin.site.register(Repo, RepoAdmin)
