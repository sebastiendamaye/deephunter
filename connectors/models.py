from django.db import models

class Connector(models.Model):
    DOMAIN_CHOICES = [
        ('analytics', 'Analytics'),
        ('repos', 'Repos'),
    ]

    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=False)
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES, blank=True)

    def __str__(self):
        return self.name

class ConnectorConf(models.Model):
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE)
    key = models.CharField(max_length=50)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.connector.name}:{self.key}"

