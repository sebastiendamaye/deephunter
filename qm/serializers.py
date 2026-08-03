"""
Serializers for the DeepHunter REST API.

These serializers are designed to be friendly to programmatic clients (e.g. an
external AI assistant creating analytics). Related objects are referenced by
their human-readable natural keys (names / MITRE IDs) rather than by database
primary keys, so callers don't need to know internal IDs.
"""
from rest_framework import serializers

from connectors.models import Connector
from .models import (
    Analytic, Category, Tag, MitreTechnique, ThreatName, ThreatActor,
    TargetOs, Vulnerability,
)


class AnalyticSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and reading Analytic objects.

    Relations are exposed as natural keys:
      - connector            -> Connector.name (must be an enabled 'analytics' connector)
      - category             -> Category.name
      - tags                 -> Tag.name
      - mitre_techniques     -> MitreTechnique.mitre_id (e.g. "T1059.001")
      - threats              -> ThreatName.name
      - actors               -> ThreatActor.name
      - target_os            -> TargetOs.name
      - vulnerabilities      -> Vulnerability.name (e.g. "CVE-2024-1234")

    Referenced objects must already exist; unknown values raise a validation
    error rather than being created implicitly.
    """
    # Only enabled analytics connectors are selectable, matching the web UI.
    connector = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Connector.objects.filter(domain='analytics', enabled=True),
        help_text="Name of an enabled 'analytics' connector.",
    )
    category = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Category.objects.all(),
        required=False, allow_null=True,
    )
    tags = serializers.SlugRelatedField(
        slug_field='name', queryset=Tag.objects.all(),
        many=True, required=False,
    )
    mitre_techniques = serializers.SlugRelatedField(
        slug_field='mitre_id', queryset=MitreTechnique.objects.all(),
        many=True, required=False,
    )
    threats = serializers.SlugRelatedField(
        slug_field='name', queryset=ThreatName.objects.all(),
        many=True, required=False,
    )
    actors = serializers.SlugRelatedField(
        slug_field='name', queryset=ThreatActor.objects.all(),
        many=True, required=False,
    )
    target_os = serializers.SlugRelatedField(
        slug_field='name', queryset=TargetOs.objects.all(),
        many=True, required=False,
    )
    vulnerabilities = serializers.SlugRelatedField(
        slug_field='name', queryset=Vulnerability.objects.all(),
        many=True, required=False,
    )
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Analytic
        fields = [
            'id', 'name', 'description', 'notes', 'created_by', 'pub_date',
            'status', 'confidence', 'relevance', 'category',
            'weighted_relevance', 'connector', 'query', 'columns', 'tags',
            'mitre_techniques', 'threats', 'actors', 'target_os',
            'vulnerabilities', 'emulation_validation', 'references',
            'create_rule', 'run_daily', 'run_daily_lock', 'dynamic_query',
            'anomaly_threshold_count', 'anomaly_threshold_endpoints',
        ]
        # repo is editable=False; created_by / pub_date / weighted_relevance
        # are managed by the server.
        read_only_fields = ['id', 'created_by', 'pub_date', 'weighted_relevance']

    def validate_status(self, value):
        # Mirror the web UI: only DRAFT and PUB are allowed at creation time.
        if self.instance is None and value not in ('DRAFT', 'PUB'):
            raise serializers.ValidationError(
                "Only 'DRAFT' or 'PUB' status is allowed when creating an analytic."
            )
        return value

    def validate_query(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Query cannot be empty.")
        return value


class ConnectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Connector
        fields = ['name', 'description']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'short_name', 'description']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name']


class MitreTechniqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = MitreTechnique
        fields = ['mitre_id', 'name', 'is_subtechnique']


class ThreatNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThreatName
        fields = ['name', 'aka_name']


class ThreatActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThreatActor
        fields = ['name', 'aka_name']


class TargetOsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetOs
        fields = ['name']


class VulnerabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vulnerability
        fields = ['name', 'base_score', 'description']
