REST API
########

DeepHunter exposes a REST API for creating, reading and updating
threat-hunting analytics programmatically. It is intended for automation clients such as an
external AI assistant running on a separate server.

The API is built with `Django REST Framework <https://www.django-rest-framework.org/>`_
and uses `django-rest-knox <https://jazzband.github.io/django-rest-knox/>`_ for
token authentication.

Installation
============

The API requires two extra Python packages (already listed in
``requirements.txt``)::

    djangorestframework
    django-rest-knox

Install them in the virtual environment and run migrations to create the Knox
token table::

    source /data/venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate

Apache configuration
--------------------

DeepHunter runs under Apache with mod_wsgi. By default, mod_wsgi **strips the
HTTP** ``Authorization`` **header**, so the API's token authentication
(``Authorization: Token <token>``) never reaches Django and every request fails
with ``{"detail": "Authentication credentials were not provided."}``.

Add the following directive to the ``<VirtualHost>`` of the DeepHunter site
(alongside the other ``WSGI*`` directives)::

    WSGIPassAuthorization On

.. note::

   The template shipped in
   ``install/etc/apache2/sites-available/deephunter-ssl.conf`` already includes
   this directive. If you deployed before it was added, edit your live vhost
   under ``/etc/apache2/sites-available/`` and add it manually.

Then reload Apache so the WSGI workers pick up the new code and settings::

    sudo systemctl reload apache2

Authentication
==============

Authentication is token-based. A client sends a Knox token on every request.

There is **no password login endpoint**. DeepHunter authenticates users through
an external provider (PingID / EntraID), so accounts have no local password to
exchange for a token. Tokens are instead issued out-of-band by an administrator
using a management command, then handed to the client.

Obtain a token
--------------

On the server, with the virtual environment active, run the
``create_api_token`` management command for an existing user::

    source /data/venv/bin/activate
    python manage.py create_api_token <username>

The plaintext token is printed once::

    API token for '<username>' (valid for 90 day(s)):

        9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b...

Options:

* ``--days N`` — token lifetime in days (default: ``90``). Overrides the global
  ``REST_KNOX['TOKEN_TTL']`` for this token only.
* ``--no-expiry`` — mint a non-expiring token (rotate/revoke manually); suited
  to headless service accounts.
* ``--grant-perms`` — also grant the model permissions the API requires
  (``qm.view_analytic``, ``qm.add_analytic``, ``qm.view_tag``, ``qm.add_tag``).
* ``--grant-change-perms`` — also grant the permissions needed to modify
  existing analytics (``qm.change_analytic``, ``qm.change_analytic_status``).
  Kept separate from ``--grant-perms`` so a token can create analytics without
  being able to modify (e.g. unpublish or archive) existing ones.

Only a hash of the token is stored server-side; the plaintext value is shown
only once, at creation, and cannot be retrieved again. If it is lost, generate
a new token (and revoke the old one — see `Revoke a token`_).

Use the token
-------------

.. code-block:: bash

    curl https://deephunter.domain.tld/api/analytics/ \
         -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b..."

Revoke a token
--------------

* ``POST /api/auth/logout/`` — invalidate the token used for the request.
* ``POST /api/auth/logoutall/`` — invalidate all of the user's tokens.

An administrator can also revoke tokens by deleting the corresponding
``knox.AuthToken`` rows (e.g. from the Django admin or shell).

Renew a token
-------------

To renew a token before it expires, simply run ``create_api_token`` again for
the same user::

    python manage.py create_api_token <username>

Each run mints a **new, independent token** — it does not reuse or overwrite the
previous one (Knox stores only a hash and cannot reproduce an existing token).
Because there is no per-user token limit
(``REST_KNOX['TOKEN_LIMIT_PER_USER']`` is ``None``), the old token remains valid
until its own expiry, so the two coexist during the changeover.

The recommended renewal procedure is therefore:

#. Generate the new token and deploy it to the client.
#. Once the client is using the new token, revoke the old one (see
   `Revoke a token`_) so it does not linger until expiry.

Authorization
=============

The API reuses DeepHunter's existing Django model permissions. The user tied
to the token must hold the relevant permissions:

* ``qm.view_analytic`` — to list/retrieve analytics and read run status.
* ``qm.add_analytic`` — to create analytics.
* ``qm.change_analytic`` — to update analytics (``PATCH`` / ``PUT``).
* ``qm.change_analytic_status`` — additionally required when an update changes
  an analytic's ``status``.
* ``qm.view_tag`` — to list tags.
* ``qm.add_tag`` — to create tags.
* ``qm.view_savedsearch`` — to list hunting packages (saved searches).
* ``qm.view_endpoint`` — to read a hunting package's matching endpoints.

It is recommended to create a dedicated service account for the AI assistant,
grant it only these permissions, and use its token.

Endpoints
=========

Analytics
---------

``GET /api/analytics/``
    List all analytics, except archived ones (status ``ARCH``).

``POST /api/analytics/``
    Create a new analytic. ``created_by`` is set automatically to the
    authenticated user. Only ``DRAFT`` and ``PUB`` status values are accepted
    at creation, matching the web UI. Creating an analytic triggers the same
    server-side behaviour as the UI (``AnalyticMeta`` creation, optional remote
    detection-rule sync, and automatic stats regeneration).

``GET /api/analytics/<id>/``
    Retrieve a single analytic.

.. note::

    Archived analytics (status ``ARCH``) are not exposed by the API: they are
    omitted from the list, and retrieving, updating or querying the run status
    of an archived analytic returns ``404 Not Found``. Archiving an analytic
    through ``PATCH`` is allowed, after which it is no longer visible.

``PATCH /api/analytics/<id>/``
    Partially update an analytic: only the fields sent are changed. ``PUT``
    performs a full update (``name``, ``connector`` and ``query`` required).
    See `Update an analytic`_ below. Requires ``qm.change_analytic``.

``GET /api/analytics/<id>/status/``
    Report the run/completion status of the analytic's stats regeneration and,
    once complete, the number of distinct endpoints it matched. See
    `Analytic run status`_ below.

Related objects are referenced by their **natural keys**, not database IDs:

============================  ===========================================
Field                         Reference value
============================  ===========================================
``connector``                 Connector name (enabled ``analytics`` connector)
``category``                  Category name
``tags``                      Tag names
``mitre_techniques``          MITRE technique IDs (e.g. ``T1059.001``)
``threats``                   Threat names
``actors``                    Threat actor names
``target_os``                 Target OS names
``vulnerabilities``           CVE identifiers (e.g. ``CVE-2024-1234``)
============================  ===========================================

Referenced objects must already exist; unknown values return a validation
error. Tags are the exception: a missing tag can be created first via the
``/api/tags/`` endpoint (see below), then referenced by name.

Query and columns
~~~~~~~~~~~~~~~~~

An analytic's query is split across two fields:

``query``
    The filter logic only. When DeepHunter runs the analytic (daily campaign,
    stats regeneration), it appends its own aggregation to this field, e.g.
    ``| group nb=count(), ... by endpoint.name, site.name`` for SentinelOne or
    ``| summarize count() by Computer`` for Microsoft Defender. It is also the
    query synced as a remote detection rule (``create_rule``).

``columns``
    Optional display-only pipe, appended to ``query`` (on a new line) **only**
    to build the "open in console" link. Write the full pipe statement, as you
    would type it in the console.

For example, the SentinelOne query
``src.process.name='oops.exe' | columns event.time, src.process.name, src.process.cmdline``
must be sent as::

    "query":   "src.process.name='oops.exe'",
    "columns": "| columns event.time, src.process.name, src.process.cmdline"

Leaving ``| columns`` in ``query`` would drop ``endpoint.name`` and
``site.name`` before DeepHunter's aggregation, breaking the run and the stats.
For the ``sentinelone`` connector, the API therefore **rejects** (``400``) a
``query`` containing a ``| columns`` pipe, on both creation and update.

.. note::

   For Microsoft Defender, a ``| project Computer = ...`` transformation needed
   to define the ``Computer`` column must stay in ``query``; only display
   projections belong in ``columns``.

Tags
----

``GET /api/tags/``
    List all tags. Returns the same data as ``GET /api/ref/tags/``.

``POST /api/tags/``
    Create a new tag. The body is a single ``name`` field (max 20 characters,
    must be unique). This lets a client create a missing tag before referencing
    it from a new analytic, instead of the analytic creation failing on an
    unknown tag.

Requires ``qm.view_tag`` (list) / ``qm.add_tag`` (create).

.. code-block:: bash

    curl -X POST https://deephunter.domain.tld/api/tags/ \
         -H "Authorization: Token $TOKEN" \
         -H "Content-Type: application/json" \
         -d '{"name": "lolbin"}'

Response (``201 Created``)::

    {"name": "lolbin"}

Posting a name that already exists returns a ``400`` validation error.

Hunting packages (saved searches)
---------------------------------

A *hunting package* (saved search) bundles a set of analytic filters (free-text
search, connectors, categories, tags, MITRE techniques, threats, actors, ...)
under a unique name. These endpoints let a client find how many endpoints match
a package and list them.

``GET /api/saved-searches/``
    List hunting packages. **Only saved searches with "public" visibility are
    listed** (plus any created by the authenticated user's own account) —
    private searches owned by other users are not returned. Since the MCP
    connects as a dedicated service account that typically owns no searches,
    this effectively lists only public packages; to expose a private search,
    its owner must mark it public. Returns ``[{name, description, is_public}]``.
    Requires ``qm.view_savedsearch``.

``GET /api/saved-searches/endpoints/?name=<name>``
    Report the distinct endpoints matching a hunting package's filters. The
    package is identified by its ``name`` query parameter (names may contain
    spaces, so URL-encode it). Requires ``qm.view_endpoint``.

    The package's filters are resolved to the matching analytics (the same
    logic as the web UI), then the distinct endpoints across those analytics'
    runs are aggregated.

.. code-block:: bash

    curl -G https://deephunter.domain.tld/api/saved-searches/endpoints/ \
         --data-urlencode "name=Emotet hunting" \
         -H "Authorization: Token $TOKEN"

Response::

    {
        "name": "Emotet hunting",
        "analytics_count": 7,
        "endpoints_count": 3,
        "endpoints": [
            {"hostname": "WKS-001", "site": "HQ", "analytics_count": 4},
            {"hostname": "WKS-042", "site": "HQ", "analytics_count": 2},
            {"hostname": "SRV-DC1", "site": "DC", "analytics_count": 1}
        ]
    }

* ``analytics_count`` (top level) — number of analytics matching the package.
* ``endpoints_count`` — number of distinct endpoints (hostname/site pairs).
* ``endpoints[].analytics_count`` — how many of the matching analytics hit that
  endpoint (the list is ordered by this count descending, then hostname).

An unknown or non-visible package name returns ``404 Not Found``; omitting
``name`` returns ``400``.

Reference data (read-only)
--------------------------

To discover the valid natural-key values a client can reference, use the
read-only reference endpoints:

* ``GET /api/ref/connectors/``
* ``GET /api/ref/categories/``
* ``GET /api/ref/tags/``
* ``GET /api/ref/mitre-techniques/``
* ``GET /api/ref/threats/``
* ``GET /api/ref/actors/``
* ``GET /api/ref/target-os/``
* ``GET /api/ref/vulnerabilities/``

Examples
========

All requests send the token in the ``Authorization`` header. In the examples
below it is stored in a shell variable for brevity::

    TOKEN=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b...

List available connectors
--------------------------

Discover the connector names you can reference when creating an analytic:

.. code-block:: bash

    curl https://deephunter.domain.tld/api/ref/connectors/ \
         -H "Authorization: Token $TOKEN"

Response::

    [
        {"name": "sentinelone", "description": "SentinelOne Deep Visibility"},
        {"name": "defender", "description": "Microsoft Defender for Endpoint"}
    ]

The other reference endpoints work the same way. For example, list categories::

    curl https://deephunter.domain.tld/api/ref/categories/ \
         -H "Authorization: Token $TOKEN"

Response::

    [
        {"name": "Execution", "short_name": "exec", "description": "..."},
        {"name": "Persistence", "short_name": "persist", "description": "..."}
    ]

or MITRE techniques (referenced by ``mitre_id``)::

    curl https://deephunter.domain.tld/api/ref/mitre-techniques/ \
         -H "Authorization: Token $TOKEN"

Response::

    [
        {"mitre_id": "T1059.001", "name": "PowerShell", "is_subtechnique": true},
        {"mitre_id": "T1218.011", "name": "Rundll32", "is_subtechnique": true}
    ]

List analytics
--------------

.. code-block:: bash

    curl https://deephunter.domain.tld/api/analytics/ \
         -H "Authorization: Token $TOKEN"

Returns a JSON array of analytics (archived ones excluded), each in the same
shape as a single retrieve (see below).

Read a single analytic
----------------------

Retrieve one analytic by its numeric ``id``:

.. code-block:: bash

    curl https://deephunter.domain.tld/api/analytics/42/ \
         -H "Authorization: Token $TOKEN"

Response (relations are returned as natural keys, not database IDs)::

    {
        "id": 42,
        "name": "Suspicious rundll32 network activity",
        "description": "Detects rundll32.exe making network connections.",
        "notes": "",
        "created_by": "svc-ai-assistant",
        "pub_date": "2026-08-03T09:15:00Z",
        "status": "PUB",
        "confidence": 2,
        "relevance": 3,
        "weighted_relevance": 6,
        "category": "Execution",
        "connector": "sentinelone",
        "query": "...",
        "columns": "...",
        "tags": ["network", "lolbin"],
        "mitre_techniques": ["T1218.011"],
        "threats": [],
        "actors": [],
        "target_os": ["Windows"],
        "vulnerabilities": [],
        "emulation_validation": "",
        "references": "",
        "create_rule": false,
        "run_daily": true,
        "run_daily_lock": false,
        "dynamic_query": false,
        "anomaly_threshold_count": null,
        "anomaly_threshold_endpoints": null
    }

A request for an unknown or archived ``id`` returns ``404 Not Found``.

Analytic run status
-------------------

When an analytic is created (or its query changes), DeepHunter runs its query
over the retention window as a background Celery task (``regenerate_stats``).
This endpoint lets a client poll that run to completion and, once complete,
read how many distinct endpoints the analytic matched — a measure of the
analytic's prevalence/noisiness.

.. code-block:: bash

    curl https://deephunter.domain.tld/api/analytics/42/status/ \
         -H "Authorization: Token $TOKEN"

While the run is in progress (``state`` is ``running``)::

    {
        "id": 42,
        "name": "Suspicious rundll32 network activity",
        "state": "running",
        "progress": 63.3,
        "last_run_date": null,
        "distinct_endpoints": null
    }

Once the run has completed (``state`` is ``complete``)::

    {
        "id": 42,
        "name": "Suspicious rundll32 network activity",
        "state": "complete",
        "progress": 100.0,
        "last_run_date": "2026-08-17",
        "distinct_endpoints": 128
    }

If the analytic has never been run, ``state`` is ``never_run`` and both
``last_run_date`` and ``distinct_endpoints`` are ``null``.

Fields:

* ``state`` — ``running`` (a run is in progress), ``complete`` (a previous run
  finished and results are available), or ``never_run`` (no snapshot exists).
* ``progress`` — completion percentage ``0``–``100`` while ``running``,
  ``100`` when ``complete``, ``null`` when ``never_run``.
* ``last_run_date`` — date of the most recent snapshot, or ``null``.
* ``distinct_endpoints`` — number of distinct endpoints (hostnames) matched
  across all of the analytic's runs; populated **only** when ``complete``.

Typical usage from a client that just created an analytic: poll this endpoint
(e.g. every few seconds) until ``state`` is ``complete``, then read
``distinct_endpoints``. Requires ``qm.view_analytic``.

When a regeneration is triggered, all existing stats of the analytic are
deleted first, so the run starts from a pristine state (the trend graph never
mixes old and recomputed stats). If the analytic's query is changed again while
a run is still in progress (e.g. through ``PATCH /api/analytics/<id>/``), the
running regeneration is cancelled and a new run starts from scratch with the
new query. ``progress`` therefore restarts from ``0``. Only one regeneration runs at a time for a given analytic, and renaming
an analytic during a run does not lose track of it.

Create an analytic (minimal)
----------------------------

Only three fields are required: ``name``, ``connector``, and ``query``. Every
other field falls back to its default (``status`` → ``DRAFT``, ``confidence``
→ ``1``, ``relevance`` → ``1``, ``run_daily`` → ``true``, and so on):

.. code-block:: bash

    curl -X POST https://deephunter.domain.tld/api/analytics/ \
         -H "Authorization: Token $TOKEN" \
         -H "Content-Type: application/json" \
         -d '{
               "name": "Suspicious rundll32 network activity",
               "connector": "sentinelone",
               "query": "..."
             }'

Create an analytic (full)
-------------------------

The same request with every writable field populated (descriptive, scoring,
relation, behaviour and anomaly-threshold fields):

.. code-block:: bash

    curl -X POST https://deephunter.domain.tld/api/analytics/ \
         -H "Authorization: Token $TOKEN" \
         -H "Content-Type: application/json" \
         -d '{
               "name": "Suspicious rundll32 network activity",
               "description": "Detects rundll32.exe making network connections.",
               "notes": "Investigate the parent process and destination host.",
               "connector": "sentinelone",
               "query": "...",
               "columns": "| columns event.time, endpoint.name, src.process.cmdline",
               "status": "DRAFT",
               "confidence": 2,
               "relevance": 3,
               "category": "Execution",
               "tags": ["network", "lolbin"],
               "mitre_techniques": ["T1218.011"],
               "threats": [],
               "actors": [],
               "target_os": ["Windows"],
               "vulnerabilities": [],
               "emulation_validation": "Run rundll32 with a URL argument.",
               "references": "https://attack.mitre.org/techniques/T1218/011/",
               "create_rule": false,
               "run_daily": true,
               "run_daily_lock": false,
               "dynamic_query": false,
               "anomaly_threshold_count": 2,
               "anomaly_threshold_endpoints": 2
             }'

In both cases the response is ``201 Created`` with the full analytic (same
shape as the retrieve example above), including the server-assigned ``id``,
``created_by``, ``pub_date``, and ``weighted_relevance``.

.. note::

   Every field other than ``name``, ``connector`` and ``query`` is optional and
   falls back to its default. Relations (``category``, ``tags``,
   ``mitre_techniques``, ``threats``, ``actors``, ``target_os``,
   ``vulnerabilities``) are referenced by natural key and — with the exception
   of ``tags`` when created through the MCP server (see below) — must already
   exist, otherwise the request returns a ``400`` validation error. To create a
   missing tag through the REST API, ``POST`` it to ``/api/tags/`` first.

Update an analytic
------------------

Send only the fields to change with ``PATCH``; every other field keeps its
current value:

.. code-block:: bash

    curl -X PATCH https://deephunter.domain.tld/api/analytics/42/ \
         -H "Authorization: Token $TOKEN" \
         -H "Content-Type: application/json" \
         -d '{
               "query": "...",
               "confidence": 3,
               "tags": ["network", "lolbin", "rundll32"]
             }'

The response is ``200 OK`` with the full updated analytic (same shape as the
retrieve example above).

Rules:

* **Permissions.** The token's user needs ``qm.change_analytic``, otherwise the
  request returns ``403 Forbidden``. If the update changes ``status``, the user
  also needs ``qm.change_analytic_status`` (``403`` otherwise). Sending the
  current status unchanged does not require it.
* **Status workflow.** A status change must be allowed by the same workflow as
  the web UI edit form (e.g. ``DRAFT`` → ``PUB`` / ``ARCH``; an analytic in
  ``REVIEW`` cannot change status through an edit). A disallowed transition
  returns a ``400`` validation error listing the allowed statuses.
* **List relations are replaced**, not merged: ``tags``, ``mitre_techniques``,
  ``threats``, ``actors``, ``target_os`` and ``vulnerabilities`` are set to
  exactly the list sent (``[]`` clears it). Referenced objects must already
  exist, as for creation.
* ``id``, ``created_by``, ``pub_date`` and ``weighted_relevance`` are read-only
  and cannot be modified.
* Saving goes through the same model logic as the web UI: changing the
  ``query`` resets the analytic's error flag, triggers the optional remote
  rule sync, and regenerates its stats (poll `Analytic run status`_), and a
  ``PENDING`` analytic whose query changes moves back to ``DRAFT``.
