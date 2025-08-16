from django.db import models
class Repo(models.Model):
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField(unique=True)
    nb_analytics = models.IntegerField(null=True, blank=True, editable=False)
    nb_analytics_valid = models.IntegerField(null=True, blank=True, editable=False)
    nb_analytics_errors = models.IntegerField(null=True, blank=True, editable=False)
    last_check_date = models.DateTimeField(null=True, blank=True, editable=False)
    last_sync_date = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return self.name
