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
from django.db.models import Count, Q
from django.http import QueryDict
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from connectors.models import Connector
from .models import (
    Analytic, Category, Tag, MitreTechnique, ThreatName, ThreatActor,
    TargetOs, Vulnerability, Snapshot, Endpoint, TasksStatus, SavedSearch,
)
from .serializers import (
    AnalyticSerializer, ConnectorSerializer, CategorySerializer, TagSerializer,
    MitreTechniqueSerializer, ThreatNameSerializer, ThreatActorSerializer,
    TargetOsSerializer, VulnerabilitySerializer, SavedSearchSerializer,
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


class AnalyticRunStatusView(APIView):
    """
    GET /api/analytics/<id>/status/

    Report the completion status of an analytic's stats run and, once the run
    has completed, the number of distinct endpoints the analytic matched.

    DeepHunter runs an analytic's query over the retention window as a Celery
    task (``regenerate_stats``), which is triggered automatically when an
    analytic is created or its query changes (including via ``POST
    /api/analytics/``). While that task runs, a ``TasksStatus`` row exists whose
    ``progress`` climbs from 0 to 100; the row is deleted on completion. A
    programmatic client (e.g. the AI assistant) can therefore create an analytic
    and poll this endpoint until it reports ``complete`` to learn how prevalent
    the analytic is (its distinct-endpoint count).

    Response fields:
      - ``state``: one of ``running`` | ``complete`` | ``never_run``.
      - ``progress``: percentage 0-100 while ``running``; 100 when ``complete``;
        null when ``never_run``.
      - ``last_run_date``: date of the most recent snapshot, or null.
      - ``distinct_endpoints``: number of distinct endpoints (hostnames) matched
        across all of the analytic's runs; populated only when ``complete``
        (null while running or never run).

    Read access requires the ``qm.view_analytic`` permission, like the other
    read endpoints.
    """
    # DjangoModelPermissions resolves the required permission from this queryset,
    # so a GET here maps to 'qm.view_analytic'.
    queryset = Analytic.objects.all()
    permission_classes = [StrictDjangoModelPermissions]

    def get(self, request, pk):
        analytic = get_object_or_404(Analytic, pk=pk)

        # A TasksStatus row keyed on the analytic name means a run is in
        # progress; it is deleted by regenerate_stats() once the run completes.
        task = TasksStatus.objects.filter(taskname=analytic.name).first()
        if task is not None:
            return Response({
                'id': analytic.id,
                'name': analytic.name,
                'state': 'running',
                'progress': round(task.progress, 1),
                'last_run_date': None,
                'distinct_endpoints': None,
            })

        # No task row: the run is not in progress. If there is no snapshot at
        # all, the analytic has never been run.
        last_snapshot = Snapshot.objects.filter(analytic=analytic).order_by('-date').first()
        if last_snapshot is None:
            return Response({
                'id': analytic.id,
                'name': analytic.name,
                'state': 'never_run',
                'progress': None,
                'last_run_date': None,
                'distinct_endpoints': None,
            })

        # Completed run: count distinct endpoints (hostnames) across all of the
        # analytic's snapshots (same computation as the web trend view).
        distinct_endpoints = (
            Endpoint.objects
            .filter(snapshot__analytic=analytic)
            .values('hostname')
            .distinct()
            .count()
        )
        return Response({
            'id': analytic.id,
            'name': analytic.name,
            'state': 'complete',
            'progress': 100.0,
            'last_run_date': last_snapshot.date,
            'distinct_endpoints': distinct_endpoints,
        })


class _FilterQueryRequest:
    """Minimal stand-in for a Django request exposing only ``.GET``.

    The shared ``filter_analytics()`` view helper reads its filters exclusively
    from ``request.GET`` (a ``QueryDict``). A hunting package (``SavedSearch``)
    stores its whole filter set as a URL-encoded query string in its ``search``
    field, so wrapping that string in a ``QueryDict`` lets us reuse the exact
    same filtering logic the web UI uses, without duplicating it.
    """
    def __init__(self, query_string):
        self.GET = QueryDict((query_string or '').lstrip('?'))


def _visible_saved_searches(user):
    """Saved searches a user may see: public ones plus their own.

    Mirrors the visibility rule enforced in the web UI so the API does not
    expose another user's private hunting packages.
    """
    return SavedSearch.objects.filter(Q(is_public=True) | Q(created_by=user))


class SavedSearchListView(generics.ListAPIView):
    """
    GET /api/saved-searches/   List hunting packages (saved searches).

    Returns the packages visible to the authenticated user (public ones plus
    their own), so a client can discover the exact name to pass to the
    endpoints report below. Requires 'qm.view_savedsearch'.
    """
    serializer_class = SavedSearchSerializer
    permission_classes = [StrictDjangoModelPermissions]
    # DjangoModelPermissions resolves the required perm from this model.
    queryset = SavedSearch.objects.all()

    def get_queryset(self):
        return _visible_saved_searches(self.request.user).order_by('name')


class SavedSearchEndpointsView(APIView):
    """
    GET /api/saved-searches/endpoints/?name=<name>

    Given a hunting package (saved search) name, report how many distinct
    endpoints match its filters and list those endpoints.

    A hunting package stores a set of filters (free-text search, connectors,
    categories, tags, MITRE techniques, threats, actors, ...). Those filters
    select a set of analytics; each analytic's runs record the endpoints
    (hostnames) it matched. This endpoint resolves the package's filters to the
    matching analytics (reusing the same logic as the web UI), then aggregates
    the distinct endpoints across those analytics' runs.

    Response fields:
      - ``name``: the resolved saved-search name.
      - ``analytics_count``: number of analytics matching the package filters.
      - ``endpoints_count``: number of distinct endpoints (hostname/site pairs).
      - ``endpoints``: list of ``{hostname, site, analytics_count}`` where
        ``analytics_count`` is how many of the matching analytics hit that
        endpoint, ordered by that count descending then hostname.

    Requires 'qm.view_endpoint' (matching the web endpoints report).
    """
    # DjangoModelPermissions resolves the required perm from this model, so a
    # GET here maps to 'qm.view_endpoint'.
    queryset = Endpoint.objects.all()
    permission_classes = [StrictDjangoModelPermissions]

    def get(self, request):
        name = request.query_params.get('name')
        if not name:
            return Response(
                {'detail': "Query parameter 'name' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        saved_search = get_object_or_404(
            _visible_saved_searches(request.user), name=name
        )

        # Reuse the web UI's filtering logic. Imported lazily to avoid coupling
        # the API module's import to the (heavier) views module at load time.
        from .views import filter_analytics
        analytics, _, _ = filter_analytics(_FilterQueryRequest(saved_search.search))

        endpoints = list(
            Endpoint.objects
            .filter(snapshot__analytic__in=analytics)
            .values('hostname', 'site')
            .annotate(analytics_count=Count('snapshot__analytic', distinct=True))
            .order_by('-analytics_count', 'hostname')
        )

        return Response({
            'name': saved_search.name,
            'analytics_count': analytics.count(),
            'endpoints_count': len(endpoints),
            'endpoints': endpoints,
        })


class TagListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/tags/       List tags.
    POST /api/tags/       Create a new tag.

    Tags are otherwise expected to already exist when referenced from an
    analytic. This endpoint lets a client (e.g. the AI assistant) create a
    missing tag first, so analytic creation does not fail on an unknown tag.
    Creating requires the 'qm.add_tag' permission (listing 'qm.view_tag').
    """
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
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
