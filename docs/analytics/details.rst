Analytic details tab
####################

Actions buttons
***************

- **Run query**: Plays the corresponding query in a new window.
- **See trend**: Opens the `trend analysis page <modules/trend.html>`_.
- **Edit in admin**: Opens the threat hunting in edit mode using the Django admin backend.
- **Delete stats**: Deletes the statistics of the selected threat hunting analytic for the entire retention. This can be used when the analytic is not relevant enough to be scheduled in the campaigns, but existing statistics are present in the database (from previous campaigns).
- **Regenerate stats**: Regenerates the statistics for the entire retention for the threat hunting analytic. This process runs in the background using Celery/Redis. You can close the page, and the process will continue to run. A percentage of completion is shown in real time.

Header Information
******************

- **top 10 endpoints + see all endpoints**: Shows the list of top 10 endpoints identified by the last campaign. Clicking on an endpoint will open a new window, loaded with the `timeline <modules/timeline.html>`_ of the selected endpoint. If there are more than 10 endpoints, the ``see all endpoints`` link redirects to the backend to show the full list of endpoints.
- **Created on, last modified on, history**: Date of creation and last modification. The ``history`` link shows all modifications, user and date for the analytic. It relies on the ``django-simple-history`` package.
- **Tags**: list of selected tags for the threat hunting analytic.

Sections
********

- **Description**: This is the description of the threat hunting analytic. It uses the markdown syntax to format the text, and possibly add subsections (e.g., description, offensive tradecraft, examples, etc.)
- **Threat Hunting Notes**: Notes to help threat hunters to triage events. For example, it can be used to inform about known false positives, or describe some exclusions.
- **PowerQuery**: The PowerQuery, including columns (the query and the columns are in 2 separate fields in the database).
- **Threat Coverage**: shows the OS covered by the threat hunting analytic, vulnerabilities covered, associated threat actors and associated threats. 
- **MITRE Information**: MITRE coverage (tactics, techniques and sub-techniques).
- **Emulation & Validation**: Shows steps to emulate a behavior that will trigger the analytic. It uses the markdown syntax.
- **References**: a list of links to learn more about the threat hunting analytic.
