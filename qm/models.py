from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
from connectors.models import Connector
from repos.models import Repo

class Country(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "countries"

class MitreTactic(models.Model):
    mitre_id = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    position = models.IntegerField(blank=False)
    
    def __str__(self):
        return '{} - {}'.format(self.mitre_id, self.name)
    
    class Meta:
        ordering = ['position']

class MitreTechnique(models.Model):
    mitre_id = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=150)
    is_subtechnique = models.BooleanField() 
    mitre_technique = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE)
    mitre_tactic = models.ManyToManyField(MitreTactic)
    description = models.TextField(blank=True)
    
    def __str__(self):
        if self.is_subtechnique:
            return f"{self.mitre_id} - {self.mitre_technique.name} - {self.name}"
        else:
            return f"{self.mitre_id} - {self.name}"
    
    class Meta:
        ordering = ['mitre_id']

class ThreatName(models.Model):
    name = models.CharField(max_length=100, verbose_name="Threat name or software", unique=True)
    aka_name = models.CharField(max_length=500, blank=True, help_text="Also known as, separator: comma")
    references = models.TextField(blank=True, help_text="List of sources, one per line")
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class ThreatActor(models.Model):
    name = models.CharField(max_length=100, verbose_name="Threat actor", unique=True)
    aka_name = models.CharField(max_length=500, blank=True, help_text="Also known as, separator: comma")
    source_country = models.ForeignKey(Country, blank=True, null=True, on_delete=models.CASCADE)
    references = models.TextField(blank=True, help_text="List of sources, one per line")
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class TargetOs(models.Model):
    name = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "target OS"

class Vulnerability(models.Model):
    name = models.CharField(max_length=20, verbose_name="format: CVE-XXXX-XXXX", unique=True)
    base_score = models.FloatField()
    description = models.TextField(blank=True)
    references = models.TextField(blank=True, help_text="List of sources, one per line")
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "vulnerabilities"

class Tag(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    short_name = models.CharField(max_length=4, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "categories"

class Analytic(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUB', 'Published'),
        ('REVIEW', 'To be reviewed'),
        ('ARCH', 'Archived'),
        ('PENDING', 'Pending Update'),
    ]
    CONFIDENCE_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]
    RELEVANCE_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, help_text="Description, Markdown syntax")
    repo = models.ForeignKey(Repo, on_delete=models.SET_NULL, null=True, blank=True, editable=False, help_text="Repo this analytic has been created from")
    notes = models.TextField(blank=True, help_text="Threat hunting notes, Markdown syntax")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    pub_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    confidence = models.IntegerField(choices=CONFIDENCE_CHOICES, default=1)
    relevance = models.IntegerField(choices=RELEVANCE_CHOICES, default=1)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True, null=True)
    weighted_relevance = models.GeneratedField(
        expression=models.F("relevance") * models.F("confidence")/4,
        output_field=models.FloatField(),
        db_persist=False
    )
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, help_text="Connector to use for this analytic")
    query = models.TextField(blank=False)
    columns = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    mitre_techniques = models.ManyToManyField(MitreTechnique, blank=True)
    threats = models.ManyToManyField(ThreatName, blank=True)
    actors = models.ManyToManyField(ThreatActor, blank=True)
    target_os = models.ManyToManyField(TargetOs, blank=True)
    vulnerabilities = models.ManyToManyField(Vulnerability, blank=True)
    emulation_validation = models.TextField(blank=True, help_text="Emulation and validation, Markdown syntax")
    references = models.TextField(blank=True, help_text="List of sources, one per line")
    create_rule = models.BooleanField(default=False)
    run_daily = models.BooleanField(default=True)
    run_daily_lock = models.BooleanField(default=False, help_text="Prevents the run_daily flag from being unset and stats from being deleted automatically")
    dynamic_query = models.BooleanField(default=False)
    anomaly_threshold_count = models.IntegerField(default=2, help_text="Value range from 0 to 3. The higher the less sensitive")
    anomaly_threshold_endpoints = models.IntegerField(default=2, help_text="Value range from 0 to 3. The higher the less sensitive")
    
    history = HistoricalRecords(
        # to be removed in next commit
        excluded_fields=['query_error', 'query_error_message', 'query_error_date', 'last_time_seen', 'next_review_date', 'maxhosts_count'],
        m2m_fields=[tags, mitre_techniques, threats, actors, target_os, vulnerabilities]
    )
    
    def __str__(self):
        return self.name
    
    def has_changed(self):
        if not self.pk:
            return True  # New object, definitely changed (being created)
        
        try:
            old = Analytic.objects.get(pk=self.pk)
        except Analytic.DoesNotExist:
            return True  # New object

        for field in self._meta.fields:
            field_name = field.name
            if getattr(old, field_name) != getattr(self, field_name):
                return True  # At least one field changed
        return False  # No changes

    def clean(self):
        super().clean()
        if self.query.strip() == '':
            raise ValidationError({'query': 'Query cannot be empty.'})
        
    def save(self, *args, **kwargs):
        # make sure query is not an empty string
        self.full_clean()
        # To prevent simple-history from logging useless entries (when no change)
        # we only call save method if there is a real change
        if self.has_changed():
            super().save(*args, **kwargs)

    class Meta:
        permissions = [
            ("bulk_update_analytics", "Bulk actions on analytics"),
            ("change_analytic_status", "Can change the status of analytics"),
            ("run_query", "Can run queries"),
            ("view_timeline", "Can view timeline"),
            ("view_netview", "Can view netview"),
            ("view_reports", "Can view reports"),
        ]

class AnalyticMeta(models.Model):
    analytic = models.OneToOneField(Analytic, on_delete=models.CASCADE, primary_key=True)
    maxhosts_count = models.IntegerField(default=0, help_text="Counts how many times max hosts threshold is reached")
    query_error = models.BooleanField(default=False)
    query_error_message = models.TextField(blank=True)
    query_error_date = models.DateTimeField(blank=True, null=True)
    next_review_date = models.DateField(blank=True, null=True)
    last_time_seen = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return self.analytic.name

class Campaign(models.Model):
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True)
    date_start = models.DateTimeField()
    date_end = models.DateTimeField(blank=True, null=True)
    nb_queries = models.IntegerField(default=0, help_text="Number of TH analytics targeted in this campaign")
    nb_analytics = models.IntegerField(default=0, help_text="Total number of TH analytics (even if not run in this campaign)")
    nb_endpoints = models.IntegerField(default=0, help_text="Total number of unique endpoints detected in this campaign")
    
    def __str__(self):
        return self.name

class CampaignCompletion(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE)
    nb_queries_complete = models.IntegerField(default=0, help_text="Number of TH analytics completed in this campaign for this connector")
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'connector'], name='unique_campaign_connector')
        ]
    def __str__(self):
        return f'{self.campaign.name} - {self.connector.name}'

class Snapshot(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    analytic = models.ForeignKey(Analytic, on_delete=models.CASCADE)
    date = models.DateField()
    runtime = models.FloatField()
    hits_count = models.IntegerField(default=0)
    hits_endpoints = models.IntegerField(default=0)
    zscore_count = models.FloatField(default=0)
    zscore_endpoints = models.FloatField(default=0)
    anomaly_alert_count = models.BooleanField(default=False)
    anomaly_alert_endpoints = models.BooleanField(default=False)
    
    def __str__(self):
        return '{} - {}'.format(self.date, self.analytic.name)

class Endpoint(models.Model):
    hostname = models.CharField(max_length=253)
    site = models.CharField(max_length=253, blank=True)
    snapshot = models.ForeignKey(Snapshot, on_delete=models.CASCADE)
    storylineid = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return '{} - {} - {}'.format(self.snapshot.date, self.hostname, self.snapshot.analytic.name)

class TasksStatus(models.Model):
    taskname = models.CharField(max_length=200, unique=True)
    date = models.DateTimeField(auto_now_add=True)
    progress = models.FloatField(default=0)
    taskid = models.CharField(max_length=36, blank=True)
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    def __str__(self):
        return self.taskname
    
    class Meta:
        verbose_name_plural = "Tasks status"

class Review(models.Model):
    DECISION_CHOICES = [
        ('PENDING', 'Needs to be updated'),
        ('KEEP', 'Keep it running'),
        ('LOCK', 'Keep and lock'),
        ('ARCH', 'Archive'),
        ('DEL', 'Delete'),
    ]

    analytic = models.ForeignKey(Analytic, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    comments = models.TextField(blank=True)

    def __str__(self):
        return '{} - {}'.format(self.analytic.name, self.date)

    class Meta:
        ordering = ['-date', 'analytic__name']

class SavedSearch(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    search = models.TextField()
    is_public = models.BooleanField(default=False, help_text="Public searches are visible to all users while private searches are only visible to the creator.")
    is_locked = models.BooleanField(default=False, help_text="Locked searches cannot be edited or deleted.")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    pub_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Saved searches"
