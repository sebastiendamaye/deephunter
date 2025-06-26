from django.db import models

class Connector(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class ConnectorConf(models.Model):
    TYPE_CHOICES = [
        ('char', 'String'),
        ('int', 'Integer'),
        ('float', 'Float'),
        ('bool', 'Boolean'),
    ]
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE)
    key = models.CharField(max_length=50)
    value = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=5, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.connector.name}:{self.key}"
