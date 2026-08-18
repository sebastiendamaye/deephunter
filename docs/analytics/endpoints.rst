Endpoints
#########

Description
***********
This page shows the list of **distinct endpoints** identified across all threat
hunting analytics matching a given combination of filters. It is the same set
of filters as the one available on the `List Analytics <list_analytics.html>`_
page (free-text search, connectors, categories, MITRE techniques, tags, actors,
statuses, etc.).

For each endpoint, the following columns are displayed:

- **Hostname**: name of the endpoint. Hostnames are clickable and redirect to
  the `timeline <modules/timeline.html>`_ module, where you can see more
  details about the endpoint.
- **Site**: site the endpoint belongs to.
- **# distinct analytics**: number of distinct analytics (matching the selected
  filters) for which the endpoint was identified, ordered in descending order.

A **Back to analytics** button returns to the `List Analytics <list_analytics.html>`_
page with the same filters applied.

How to access it
****************
The Endpoints page can be reached in two ways:

- From the `List Analytics <list_analytics.html>`_ page, apply some filters and
  click the **Endpoints** button (next to the **Save search** and
  **Search in admin** buttons).
- From the `Saved Searches <saved_searches.html>`_ page, click the **endpoints**
  action next to a saved search.

.. note::
   This page requires the ``qm.view_endpoint`` permission.
