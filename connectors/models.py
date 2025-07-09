from django.db import models

class Connector(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=False)
    visible_in_analytics = models.BooleanField(default=False, help_text="Should this connector be visible in threat hunting analytics?")

    def __str__(self):
        return self.name

class ConnectorConf(models.Model):
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE)
    key = models.CharField(max_length=50)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.connector.name}:{self.key}"
