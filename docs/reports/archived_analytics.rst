Archived Analytics
##################

This report is a shortcut to the backend (admin), pointing to the list of analytics filtered with the ``ARCH`` status.

Note that archived analytics are not included in the Threat Hunting campaigns, and not shown in any reports.

When an analytic is archived, the ``run_daily`` and ``run_daily_lock`` flags are automatically set to ``False``.

To restore an archived analytic, open it and change the status to ``PUB``.