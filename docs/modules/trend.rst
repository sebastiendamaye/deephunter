Trend
#####

Trend Analysis
**************
The trend analysis is a special component of threat hunting analytics, to help the threat hunter understand how frequent the analytic triggers. It shows graphs based on statistics collected daily by the campaigns cron job.

.. image:: ../img/trend_analysis.png
  :width: 1500
  :alt: Trend Analysis

There is a minimum of 3 graphs:

- **distribution of the runtime (in seconds)**: time taken to run the query associated to this analytic over time.
- **distribution of number of events**: number of events matching the query associated to this analytic for each campaign
- **distribution of number of endpoints** (unfiltered): number of endpoints matching the query associated to this analytic for each campaign. Clicking on dots will replay the query for the selected date.

The ``see endpoints`` link at the top left corner shows the list of all endpoints matching the current threat hunting analytic.

Anomaly detection
*****************
A z-score mathematical model is applied to the "number of hits" and "number of endpoints" to identify potential statistical anomalies, that are highlighted in red. It is possible to change sensitivity thresholds (click on the ``edit in admin`` link to change threshold values).

- **Anomaly threshold count**: sensitivity threshold for the "number of hits" serie
- **Anomaly threshold endpoints**: sensitivity threshold for the "number of endpoints" serie

Value range from 0 to 3. The higher the less sensitive.
