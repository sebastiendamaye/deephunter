"""
REST API views for DeepHunter.

Exposes a programmatic interface to create and read threat-hunting analytics,
intended for use by external clients such as an AI assistant running on a
separate server.

Authentication uses django-rest-knox token auth. Tokens are issued out-of-band
with the `create_api_token` management command (there is no password login
endpoint, as users authenticate through an external provider such as PingID and
have no local password). Send the token as:

    Authorization: Token <token>

Authorization reuses Django's per-model permissions: the authenticated user
must hold 'qm.view_analytic' to read and 'qm.add_analytic' to create (see
StrictDjangoModelPermissions below).
"""
from rest_framework import generics, permissions, viewsets

from connectors.models import Connector
from .models import (
    Analytic, Category, Tag, MitreTechnique, ThreatName, ThreatActor,
    TargetOs, Vulnerability,
)
from .serializers import (
    AnalyticSerializer, ConnectorSerializer, CategorySerializer, TagSerializer,
    MitreTechniqueSerializer, ThreatNameSerializer, ThreatActorSerializer,
    TargetOsSerializer, VulnerabilitySerializer,
)


class StrictDjangoModelPermissions(permissions.DjangoModelPermissions):
    """
    Like DjangoModelPermissions, but also requires the 'view' permission for
    read (GET/HEAD/OPTIONS) requests. Stock DjangoModelPermissions allows any
    authenticated user to read; for a security tool we require an explicit
    'qm.view_analytic' permission so read access is opt-in per user.
    """
    perms_map = dict(permissions.DjangoModelPermissions.perms_map)
    perms_map['GET'] = ['%(app_label)s.view_%(model_name)s']
    perms_map['HEAD'] = ['%(app_label)s.view_%(model_name)s']
    perms_map['OPTIONS'] = ['%(app_label)s.view_%(model_name)s']


class AnalyticListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/analytics/       List analytics.
    POST /api/analytics/       Create a new analytic.

    Creation mirrors the web UI: created_by is set to the authenticated user,
    only DRAFT/PUB status is accepted, and the model's save()/signals handle
    AnalyticMeta creation, optional remote rule sync, and stats regeneration.
    """
    queryset = Analytic.objects.all().order_by('name')
    serializer_class = AnalyticSerializer
    permission_classes = [StrictDjangoModelPermissions]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AnalyticRetrieveView(generics.RetrieveAPIView):
    """GET /api/analytics/<id>/   Retrieve a single analytic."""
    queryset = Analytic.objects.all()
    serializer_class = AnalyticSerializer
    permission_classes = [StrictDjangoModelPermissions]


# --- Read-only reference endpoints -----------------------------------------
# These let a client discover the valid natural-key values (connector names,
# category names, MITRE IDs, ...) it can reference when creating an analytic.

class _ReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class ConnectorRefViewSet(_ReadOnlyModelViewSet):
    """Enabled 'analytics' connectors available for new analytics."""
    queryset = Connector.objects.filter(domain='analytics', enabled=True).order_by('name')
    serializer_class = ConnectorSerializer


class CategoryRefViewSet(_ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer


class TagRefViewSet(_ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer


class MitreTechniqueRefViewSet(_ReadOnlyModelViewSet):
    queryset = MitreTechnique.objects.all().order_by('mitre_id')
    serializer_class = MitreTechniqueSerializer


class ThreatNameRefViewSet(_ReadOnlyModelViewSet):
    queryset = ThreatName.objects.all().order_by('name')
    serializer_class = ThreatNameSerializer


class ThreatActorRefViewSet(_ReadOnlyModelViewSet):
    queryset = ThreatActor.objects.all().order_by('name')
    serializer_class = ThreatActorSerializer


class TargetOsRefViewSet(_ReadOnlyModelViewSet):
    queryset = TargetOs.objects.all().order_by('name')
    serializer_class = TargetOsSerializer


class VulnerabilityRefViewSet(_ReadOnlyModelViewSet):
    queryset = Vulnerability.objects.all().order_by('name')
    serializer_class = VulnerabilitySerializer
