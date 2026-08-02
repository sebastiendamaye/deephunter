Introduction
############

What is DeepHunter?
*******************
DeepHunter is a Threat Hunting platform that features:

- `Dashboard <dashboard.html>`_ with several widgets to immediately get an overview of your threat hunting activities.
- `Repository <analytics/list_analytics.html>`_ for your threat hunting analytics shown in a sortable table.
- `Search and filters <analytics/list_analytics.html#id2>`_ (description, threat hunting notes, tags, query, OS coverage, vulnerabilities, threat actors, threat names, MITRE coverage, etc.) to find particular threat hunting analytics or group them into hunting packages.
- `Automated execution <intro.html#campaigns>`_ of threat hunting queries in daily campaigns and collection of daily statistics (number of matching events, number of matching endpoints, etc).
- `Trend analysis <analytics/trend.html>`_ with automatic detection of statistical anomalies.
- `Timeline view <timeline.html>`_ of the distribution of threat hunting analytics for a given endpoint.
- `Network view <netview.html>`_ module to analyze network activities from a host, with highlights on the destination popularity (based on your environment) and VirusTotal reputation.
- Analytics follow a `workflow <#analytic-workflow>`_ with defined statuses and a `review process <#the-review-process>`_.
- `Synchronize rules <#rules-synchronization>`_ with your data lake (e.g., SentinelOne STAR rules).
- Synchronize threat hunting analytics with remote `repositories <repos/index.html>`_ (e.g., GitHub).
- `Connectors (plugins) <plugins/index.html>`_ to connect to different data lakes (EDRs, SIEMs, etc.) and enrich context (e.g., in the timeline view). 
- `Reports <reports/index.html>`_ to get insights on your threat hunting activities (monitoring performance, checking errors, reviewing analytics with a particular status, etc.).
- `Tools <tools/index.html>`_ (extensions) to perform specific tasks, such as checking file hashes against VirusTotal or LOLDriver databases.
- `Scripts <scripts/index.html>`_ to automate various tasks.

.. image:: img/dashboard_widgets.png
  :alt: Dashboards
.. image:: img/catalog.png
  :alt: Connectors catalog
.. image:: img/deephunter_analytics.png
  :alt: DeepHunter Analytics
.. image:: img/trend_analysis.png
  :alt: DeepHunter Trend Analysis
.. image:: img/timeline.png
  :alt: DeepHunter Timeline
.. image:: img/reports_endpoints.png
  :alt: DeepHunter Reports Endpoints
.. image:: img/reports_mitre_coverage.png
  :alt: DeepHunter Reports MITRE Coverage
.. image:: img/netview.png
  :alt: DeepHunter Netview
.. image:: img/reports_stats.png
  :alt: DeepHunter Reports Stats
.. image:: img/tools_vt_hash_checker.png
  :alt: DeepHunter Tools VT

Who is DeepHunter for?
**********************
DeepHunter is an application developed by threat hunters for threat hunters, in order to automate the execution of threat hunting queries, and prioritize threat hunts. It is not intended to replace your EDR, your SIEM or your SDL, but it will dramatically help threat hunters organize their threat hunting campaigns. Targeted populations are:

- **Threat Hunters**: DeepHunter may quickly become your day-to-day threat hunting platform.
- **SOC analysts**: DeepHunter timeline module can help you triage incidents, or correlate a reported incident with other artifacts.
- **Incident Responder/Analyst**: DeepHunter timeline can show you since when a particular behavior exists, whether it has been identified as a threat by your EDR, whether it could be linked to an installed application, etc..

What data lakes are supported?
******************************
DeepHunter (from v2.0) has been designed to connect to the any data lake, provided there is a `connector <plugins/index.html>`_ (aka *plugin*), or you `develop <plugins/write_your_own.html>`_ one. There are already connectors for `SentinelOne <plugins/sentinelone.html>`_ EDR and for `Microsoft Sentinel <plugins/microsoftsentinel.html>`_, but this list is expected to grow. You are very welcome to contribute.

Architecture
************
.. image:: img/deephunter_architecture.jpg
  :width: 800
  :alt: DeepHunter architecture diagram

Campaigns and Statistics
************************

Campaigns
=========
The purpose of DeepHunter is to automate the execution of threat hunting analytics (the ones with the ``run_daily`` flag set) each day. This is done through campaigns.

A Campaign is a cron job running every day at the same time. It executes the analytics, and collects statistics (number of matching events, number of endpoints, etc.) every day for the last 24 hours, creating a baseline (`trend analysis <analytics/trend.html>`_) for each analytic. A z-score based model is then applied on these statistics to identify potential statistical anomalies.

Whenever the cron job is scheduled during the day, it will query the data from the previous day.

.. image:: img/campaign_cron.png
  :width: 1200
  :alt: Sync rule logic

Statistics regeneration
=======================
It may happen that you modify a threat hunting query for various reasons (e.g., add a filter to exclude some results). When you do so, statistics for the updated query will change. If you want to apply the same logic to all past statistics, as if the query would have always been as you just changed it, you can regenerate the statistics for this threat hunting query. It will work on the background and show the percentage of completion as shown below.

.. image:: img/analytics_regen_stats.png
  :width: 1500
  :alt: DeepHunter architecture diagram

.. note::

    Statistics can be automatically regenerated for new analytics, or when the query field of existing analytics is modified. This is controlled by the `AUTO_STATS_REGENERATION <settings.html#auto-stats-regeneration>`_ setting.

Thresholds, error detection and automation
==========================================

In order to prevent the database from being overwhelmed with useless information, several thresholds and automatic actions are available in the `settings <settings.html>`_:

- Some analytics may match too many endpoints. It is possible to define a threshold (`CAMPAIGN_MAX_HOSTS_THRESHOLD <settings.html#campaign-max-hosts-threshold>`_) to stop stroing matching endpoints in the database.
- If the above threshold is reached several times (`ON_MAXHOSTS_REACHED.THRESHOLD <settings.html#on-maxhosts-reached>`_), you can decide to automatically remove the ``run_daily`` flag of the threat hunting analytic, so that it will be removed from future campaigns. You can also configure an automatic deletion (`ON_MAXHOSTS_REACHED.DELETE_STATS <settings.html#on-maxhosts-reached>`_) of the associated statistics.

.. note::

	The actions described above won't be applied to Threat Hunting analytics that have the flag ``run_daily_lock`` set. This is a way to protect some analytics from being automatically removed from the campaigns, or have the statistics deleted.

Static vs Dynamic analytics
===========================

By default, threat hunting analytics you will create in DeepHunter will be static. They will match a hunting query that is stored in the database, and that will be executed daily by the campaigns cron job.

However, it may happen that a hunting query needs to be dynamically generated. DeepHunter is shipped with an example (``vulnerable_driver_name_detected_loldriver``) of such a query. The query for this analytic is dynamically built from a script (``./qm/scripts/vulnerable_driver_name_detected_loldriver.py``) that runs prior to each campaign. This hunting query is built from an updated list of file names matching known vulnerable drivers, published on the LOLDriver website.

Dynamic queries should have the ``Dyn. query`` flag enabled (which is just an indication, there is no control associated to this flag), to indicate that they should not be manually edited in DeepHunter. Modifications should be done through their corresponding scripts directly.

Rules synchronization
*********************

DeepHunter can synchronize its threat hunting analytics with a remote data lake, such as SentinelOne (i.e. STAR rules) or Microsoft Sentinel. This is done per connector, with the ``need_to_sync()`` method.

Modifications on analytics (creation, modification, deletion) are monitored via the *signals*. It triggers pre-save and post-save controls, with the following logic:

.. image:: img/sync_rule_logic.jpg
  :width: 1000
  :alt: Sync rule logic

Analytic Workflow
*****************

Workflow
========

Because threat hunting analytics may become obsolete with time, or need to be updated, DeepHunter has a workflow to manage the lifecycle of threat hunting analytics. The workflow is as follows:

.. image:: img/analytics_workflow.png
  :width: 1000
  :alt: Analytics workflow

.. note::

  Notice that bypassing the workflow logic and forcing statuses can be done via the `admin panel <admin/admin_interface.html#create-modify-threat-hunting-analytics>`_, if necessary.

Statuses
========
Analytic can have the following statuses:

- **DRAFT**: Analytic newly created, under observation, not yet fully tested.
- **PUB**: Published analytic, fully tested, and considered production ready. After some time, it will automatically move to **REVIEW**.
- **REVIEW**: Analytic that was in **PUB** status for some time, and neeeds to be reviewed. Use the `review tab <#the-review-process>`_ to move forward.
- **PENDING**: Analytic that has been reviewed, and is no longer considered valid for production. The run_daily flag will be automatically unset, and the analytic query should be updated ASAP.
- **ARCH**: archived analytics. They will no longer appear in DeepHunter modules and reports, but are still in the database. To restore an archived analytic, refer to this `section <reports/archived_analytics.html#archived-analytics>`_.

Clicking on the status in the analytic view will show a dropdown from which you can choose a new status. Choices are different depending on the current status and the run_daily_lock flag.

.. image:: img/analytic_status_dropdown.png
  :alt: analytic status dropdown

The "review" process
====================
The `orchestrator.sh <scripts/orchestrator.html>`_ cron job will automatically update the status of threat hunting analytics that need to be reviewed, based on their last review date (defined with the `DAYS_BEFORE_REVIEW <settings.html#days-before-review>`_ setting).

You can access the list of analytics to review from the menu (``Reports > Analytics to review``). Expand the details and click the "Review" tab.

.. image:: img/review_tab.png
  :width: 800
  :alt: Review tab

To restore a previously archived analytic, refer to `archived analytics report <reports/archived_analytics.html>`_.