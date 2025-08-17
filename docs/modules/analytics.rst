Analytics
#########

The analytics page is where you will first land once successfully logged in to DeepHunter. This is the main dashboard that shows the list of threat hunting analytics available in DeepHunter. There are many actions you can do from this screen and you can also navigate to other modules.

Interface
*********
Refer to the objects number for details.

.. image:: ../img/analytics_interface.png
  :width: 1500
  :alt: analytics interface

1. `List of analytics <#list-of-threat-hunting-analytics>`_
2. `Threat hunting analytic details <#id1>`_
3. `Search form <#id3>`_
4. `Selected filters <#id4>`_
5. `Available filters <#id5>`_

List of threat hunting analytics
********************************
This shows the list of threat hunting analytics available in the DeepHunter database. For each, you will have information shown in columns (clicking on the column header sorts the list):

- **Name**: name of the analytic
- **Status**: Status of the analytic in the `worklfow <../intro.html#analytic-workflow>`_. Clicking on a status will show a dropdown list with possible statuses that you can choose to update the analytic. This is automatically refreshed every 10 seconds.
- **Confidence**: the confidence indicator (CRIT, HIGH, MED, LOW) tells how much you can trust the analytic. If it tends to output many "false positives", the confidence will likely be "LOW". On the other hand, a confidence of "CRIT" means that all matching events are real alerts.
- **Relevance**: The relevance (CRIT, HIGH, MED, LOW) tells how bad it is for your organization if events match the threat hunting analytic, independantly from the confidence. Understand it as the "impact". It may happen that you have an analytic that matches many events, only some of which are interesting/relevant. However, you may still want to keep this rule as matches may indicate a sign of compromise. In this case, the rule may have a low confidence, with a critical relevance.
- **Run daily**: Flag indicating if the analytic is run daily (via the campaigns cron job). Remember that DeepHunter is a repository storing all threat hunting analytics, but not all of them may need to be automated. This flag is automatically refreshed every 10 seconds.
- **STAR rule**: Flag indicating if the analytic has a matching STAR rule in SentinelOne. When you modify an analytic in DeepHunter, it will update the STAR rule in S1. Deleting a threat hunting analytic associated to a STAR rule will automatically delete the STAR rule in S1. Notice that the STAR rules will have the same name as the threat hunting analytic in DeepHunter. For that reason, a best practice is to name all of your analytics using characters in ``a-z``, ``0-9`` and replace spaces with ``_``.
- **Maxhosts count**: Counts how many times ``CAMPAIGN_MAX_HOSTS_THRESHOLD`` is reached. This counter is used (check ``ON_MAXHOSTS_REACHED``) to automatically remove threat hunting analytics from future campaigns and/or delete associated statistics.
- **Dyn query**: Flag that indicates if the analytic is `static or dynamic <intro.html#static-vs-dynamic-analytics>`_.
- **Trend**: sparkline showing the trend (based on statistics collected by the campaigns) for the last 20 days.
- **Hits (24h)**: Number of matching events for the last 24h, according to the last campaign.
- **Hosts (24h)**: Number of matching unique endpoints for the last 24h, according to the last campaign.

Threat hunting analytic details 
*******************************

Details of each analytic can be viewed by clicking on the arrow on the left of each analytic name.

Actions buttons
===============

- **Run query**: Plays the corresponding query in a new window.
- **See trend**: Opens the `trend analysis page <modules/trend.html>`_.
- **Edit in admin**: Opens the threat hunting in edit mode using the Django admin backend.
- **Delete stats**: Deletes the statistics of the selected threat hunting analytic for the entire retention. This can be used when the analytic is not relevant enough to be scheduled in the campaigns, but existing statistics are present in the database (from previous campaigns).
- **Regenerate stats**: Regenerates the statistics for the entire retention for the threat hunting analytic. This process runs in the background using Celery/Redis. You can close the page, and the process will continue to run. A percentage of completion is shown in real time.

Header Information
==================

- **top 10 endpoints + see all endpoints**: Shows the list of top 10 endpoints identified by the last campaign. Clicking on an endpoint will open a new window, loaded with the `timeline <modules/timeline.html>`_ of the selected endpoint. If there are more than 10 endpoints, the ``see all endpoints`` link redirects to the backend to show the full list of endpoints.
- **Created on, last modified on, history**: Date of creation and last modification. The ``history`` link shows all modifications, user and date for the analytic. It relies on the ``django-simple-history`` package.
- **Tags**: list of selected tags for the threat hunting analytic.

Sections
========

- **Description**: This is the description of the threat hunting analytic. It uses the markdown syntax to format the text, and possibly add subsections (e.g., description, offensive tradecraft, examples, etc.)
- **Threat Hunting Notes**: Notes to help threat hunters to triage events. For example, it can be used to inform about known false positives, or describe some exclusions.
- **PowerQuery**: The PowerQuery, including columns (the query and the columns are in 2 separate fields in the database).
- **Threat Coverage**: shows the OS covered by the threat hunting analytic, vulnerabilities covered, associated threat actors and associated threats. 
- **MITRE Information**: MITRE coverage (tactics, techniques and sub-techniques).
- **Emulation & Validation**: Shows steps to emulate a behavior that will trigger the analytic. It uses the markdown syntax.
- **References**: a list of links to learn more about the threat hunting analytic.

Search form
***********
Search for a string in the threat hunting analytics names, descriptions and threat hunting notes.

Selected filters
****************
List of applied filters. Click on the cross sign to remove a specific filter.

.. image:: ../img/analytics_filters.png
  :alt: analytics filters

Available filters
*****************
The list of all possible filters, broken down into sections. Expand a section and select a filter. It will be immediately added to the list of selected filters and the page will refresh. You can add as many filters as you want. Filters from the same section are applied as a list of values (for example, if you select "Windows" and "Linux" as "Target OS", it will show the list of threat hunting analytics that cover "Windows" or "Linux").

.. image:: ../img/analytics_filters_available.png
  :alt: analytics filters available

Create/Modify/Clone analytics
*****************************
Refer to `this page <../admin.html#create-modify-threat-hunting-analytics>`_.

Saved Searches
**************
Saved searches are a way to save a search query and its filters, so you can quickly access it later. This is useful if you often search for the same criteria.

There are public saved searches and private saved searches. Public saved searches are available to all users, while private saved searches are only available to the user who created them.

You can also lock a search (useful for public saved searches) so that no one can modify or delete it.

.. image:: ../img/saved_searches.png
  :alt: saved searches
