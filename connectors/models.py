from django.db import models

class Connector(models.Model):
    DOMAIN_CHOICES = [
        ('analytics', 'Threat Hunting Analytics'),
        ('repos', 'Repositories'),
        ('ai', 'Artificial Intelligence'),
        ('extensions', 'Extensions'),
        ('authentication', 'Authentication'),
    ]

    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    installed = models.BooleanField(default=False)
    enabled = models.BooleanField(default=False)
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class ConnectorConf(models.Model):
    FIELDTYPE_CHOICES = [
        ('bool', 'Boolean'),
        ('char', 'Character'),
        ('email', 'Email address'),
        ('float', 'Float'),
        ('int', 'Integer'),
        ('ipaddress', 'IP Address'),
        ('password', 'Password'),
        ('regex', 'Regex'),
        ('url', 'URL')
    ]

    connector = models.ForeignKey(Connector, on_delete=models.CASCADE)
    key = models.CharField(max_length=50)
    value = models.TextField(blank=True)
    fieldtype = models.CharField(max_length=20, choices=FIELDTYPE_CHOICES, default='char')
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.connector.name}:{self.key}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['connector', 'key'], name='unique_connector_key')
        ]