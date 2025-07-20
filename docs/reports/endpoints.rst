Endpoints
#########

Description
***********
This report shows a list of the top 20 endpoints (highest weighted scores) identified in the last campaign.

.. image:: ../img/reports_endpoints.png
  :width: 1000
  :alt: img

The weighted score is the sum of (relevance x [confidence/4]) of every threat hunting analytics involved for the endpoint, during the last campaign.

The column "matching analytics" shows the number of analytics matching the endpoint for the last `campaign <intro.html#campaigns>`_.

Actions (links)
***************
- **Expand/collapse**: click on each row to expand or collapse the details.
- **Send to timeline**: Send the endpoint to the `timeline <modules/timeline.html>`_ module.
- **Send to Netview**: Send the endpoint to the `netview <modules/netview.html>`_ module.
- **events**: Send the PowerQuery associated to the select threat hunting analytic to SentinelOne.
- **trend**: Show the `trend <modules/trend.html>`_ graph for the selected threat hunting analytic.
- **admin**: Open the selected threat hunting analytic in the admin backend for modification.
