Write your own plugin
#####################

This section provides a guide on how to write your own plugin for DeepHunter.

Requirements
************

Database
========

Plugins' settings should be stored in the database (Connector and ConnectorConf objects).

Python file
===========

The python file should be stored in the `plugins` folder and have the same name (extension excluded) as the plugin name in the database (Connector table). It should contain all mandatory methods.

Methods are listed below (M/O = Mandatory / Optional).

.. list-table::
   :widths: 250 300 20 500 500
   :header-rows: 1

   * - Method
     - Description
     - M/O
     - inputs
     - outputs
   * - ``init_globals``
     - Define global variables and initialize them. This method should be called in the beginning of all other methods.
     - M
     - 
     - 
   * - ``query``
     - API calls to the remote data lake to query logs. Used by the "campaign" daily cron, and the "regenerate stats" script
     - M
     - * ``analytic``: Analytic object corresponding to the threat hunting analytic
       * ``from_date``: Optional start date for the query. Date received in isoformat.
       * ``to_date``: Optional end date for the query. Date received in isoformat.
     - The result of the query (array with 4 fields: endpoint.name, NULL, number of hits, NULL), or empty array if the query failed.
   * - ``need_to_sync_rule``
     - Check if the rule needs to be synced with Microsoft Sentinel. This is determined by the SYNC_RULES setting.
     - M
     - 
     - boolean (defined in a global variable, recommended to get the value from a setting in the database)
   * - ``create_rule``
     - Create a rule in the remote data lake. This method is called when the user enables the ``create_flag`` on a threat hunting analytic.
     - O
     - ``analytic``: Analytic object corresponding to the analytic.
     - JSON object containing the response from the remote data lake.
   * - ``update_rule``
     - Update a rule in the remote data lake. This method is called when the user updates a threat hunting analytic with ``create_flag`` set.
     - O
     - ``analytic``: Analytic object corresponding to the analytic.
     - JSON object containing the response from the remote data lake.
   * - ``delete_rule``
     - Deletes a rule in the remote data lake. 
     - O
     - ``analytic``: Analytic object corresponding to the analytic.
     - 
   * - ``get_threats``
     - Get threats from your EDR for a specific hostname and a date.
     - O
     - * ``hostname``: Hostname of the machine to retrieve threats for.
       * ``created_at``: Date in ISO format to filter threats created after this date.
     - List of threats (array) or ``None`` if not found.
   * - ``get_redirect_analytic_link``
     - Get the redirect link to run the analytic in the remote data lake.
     - M
     - * ``analytic``: Analytic object containing the query string and columns.
       * ``date``: Date to filter the analytic by, in ISO format (range will be date-date+1day).
       * ``endpoint_name``: Name of the endpoint to filter the analytic by.
     - String containing the redirect link for the analytic.

Template
********

You can use the following template to create your own plugin:

.. code-block:: python

    # Imports
    from connectors.utils import get_connector_conf, gzip_base64_urlencode, manage_analytic_error
    import logging
    from datetime import datetime, timedelta, timezone
    from urllib.parse import quote, unquote

    # Get an instance of a logger
    logger = logging.getLogger(__name__)

    _globals_initialized = False
    def init_globals():
        global DEBUG, TENANT_ID, CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID, WORKSPACE_ID, WORKSPACE_NAME, RESOURCE_GROUP, SYNC_RULES
        global _globals_initialized
        if not _globals_initialized:
            DEBUG = False
            TENANT_ID = get_connector_conf('microsoftsentinel', 'TENANT_ID')
            CLIENT_ID = get_connector_conf('microsoftsentinel', 'CLIENT_ID')
            # ....
            # ....
            # ....
            SYNC_RULES = get_connector_conf('microsoftsentinel', 'SYNC_RULES')
            _globals_initialized = True

    def query(analytic, from_date=None, to_date=None, debug=None):
        """
        Implement the query logic here.
        """

        init_globals()
        # ....
        
        # .... Return a list of 4 fields:
        # .... endpoint.name, NULL, number of hits, NULL)
        # .... or empty array if the query failed

    def need_to_sync_rule():
        """
        Check if the rule needs to be synced with Microsoft Sentinel.
        This is determined by the SYNC_RULES setting.
        """
        init_globals()
        return SYNC_RULES

    def create_rule(analytic):
        """
        Method if you want to create rules to the remote data lake.
        """
        init_globals()
        return False

    def update_rule(analytic):
        """
        Method if you want to update rules to the remote data lake.
        """
        init_globals()
        return False

    def delete_rule(analytic):
        """
        Method if you want to delete rules to the remote data lake.
        """
        init_globals()
        return False


    def get_redirect_analytic_link(analytic, date=None, endpoint_name=None):
        """
        Generate a URL to pre-fill the query in the remote data lake.
        """
        init_globals()
        url = ''
        return url

