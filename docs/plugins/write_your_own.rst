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

- The python file should be stored in the `plugins` folder and have the same name (extension excluded) as the plugin name in the database (Connector table).
- The plugin name shoud not contain any space or special characters. Only use lowercase letters.
- It should contain all mandatory methods.

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
     - The result of the query (array with 4 fields: endpoint.name, NULL, number of hits, NULL), or "ERROR" if the query failed.
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
   * - ``get_redirect_analytic_link``
     - Get the redirect link to run the analytic in the remote data lake.
     - M
     - * ``analytic``: Analytic object containing the query string and columns.
       * ``date``: Date to filter the analytic by, in ISO format (range will be date-date+1day).
       * ``endpoint_name``: Name of the endpoint to filter the analytic by.
     - String containing the redirect link for the analytic.
   * - ``get_threats``
     - Get threats from your EDR for a specific hostname and a date.
     - O
     - * ``hostname``: Hostname of the machine to retrieve threats for.
       * ``sincedate``: Date in ISO format to filter threats created after this date.
     - List of threats (array) or ``None`` if not found. See expected below.
   * - ``get_redirect_threats_link``
     - Generate a link to the threats page for a specific endpoint and date. Mandatory if ``get_threats()`` method is present.
     - M/O
     - * ``endpoint``: Name of the endpoint to filter the analytic by.
       * ``date``: Threat detection date, in 'YYYY-MM-DD' format.       
     - String containing the redirect link for the threats page.
   * - ``get_token_expiration``
     - Get the expiration (in days) of the API token.
     - O
     - 
     - Integer (number of days) or None (if failure).
   * - ``error_is_info``
     - Check if the query error message is an informational message (INFO) instead of an ERROR.
     - M
     - ``error``: The error message to check.
     - Boolean indicating whether the error is informational.

Template
********

You can use the following template to create your own plugin:

.. code-block:: python

    # Imports
    from connectors.utils import get_connector_conf, gzip_base64_urlencode, manage_analytic_error
    from datetime import datetime, timedelta, timezone
    from urllib.parse import quote, unquote

    _globals_initialized = False
    def init_globals():
        global DEBUG, TENANT_ID, CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID, WORKSPACE_ID, \
              WORKSPACE_NAME, RESOURCE_GROUP, SYNC_RULES, THREATS_URL, QUERY_ERROR_INFO
        global _globals_initialized
        if not _globals_initialized:
            DEBUG = False
            TENANT_ID = get_connector_conf('microsoftsentinel', 'TENANT_ID')
            CLIENT_ID = get_connector_conf('microsoftsentinel', 'CLIENT_ID')
            # ....
            # ....
            # ....
            SYNC_RULES = get_connector_conf('microsoftsentinel', 'SYNC_RULES')
            THREATS_URL = get_connector_conf('microsoftsentinel', 'THREATS_URL')
            QUERY_ERROR_INFO = get_connector_conf('microsoftsentinel', 'QUERY_ERROR_INFO')
            _globals_initialized = True

    def query(analytic, from_date=None, to_date=None, debug=None):
        """
        Implement the query logic here.
        """

        init_globals()
        # ....
        
        # .... Return a list of 4 fields:
        # .... endpoint.name, NULL, number of hits, NULL)
        # .... or "ERROR" if the query failed

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

    def get_threats(hostname, sincedate=None):
        """
        Get threats from remote data lake for a specific hostname and sincedate date.
        :param hostname: Hostname of the machine to retrieve threats for.
        :param sincedate: Date in ISO format to filter threats created after this date.
        :return: List of threats (array) or None if not found.
        """
        init_globals()

        # Expected output format example:
        threats = [
        {'threatInfo': {
            'identifiedAt': '2025-05-29T13:36:08.167000Z',
            'threatName': 'Suivie NDF 2024.xlsm',
            'analystVerdict': 'true_positive',
            'confidenceLevel': 'malicious',
            'storyline': '',
        }},
        {'threatInfo': {
            'identifiedAt': '2025-05-29T13:36:08.183000Z',
            'threatName': 'Suivie NDF 2024 (002).xlsm',
            'analystVerdict': 'true_positive',
            'confidenceLevel': 'malicious',
            'storyline': '',
        }},
        {'threatInfo': {
            'identifiedAt': '2025-05-29T13:36:12.198000Z',
            'threatName': 'A2C163C3.xlsm',
            'analystVerdict': 'true_positive',
            'confidenceLevel': 'malicious',
            'storyline': '',
        }}
        ]

        return threats

    def get_redirect_threats_link(endpoint, date):
        """
        Generate a link to the threats page for a specific endpoint and date.
        :param endpoint: The endpoint name.
        :param date: The date for which to generate the link, in 'YYYY-MM-DD' format.
        :return: A formatted URL string for the SentinelOne threats page.
        """
        init_globals()

        # do your stuff
        # ...

        # you can use a URL template using the variables and replace with corect values
        return f"https://portal.azure.com/search?host={endpoint}&date={date}"

  def error_is_info(error):
      """ 
      Check if the query error message is an informational message (INFO) instead of an ERROR.
      This is determined with a regular expression provided by the QUERY_ERROR_INFO setting.
      :param error: The error message to check.
      :return: True if the error is an informational message, False otherwise.
      """
      init_globals()
      if QUERY_ERROR_INFO:
          if re.search(QUERY_ERROR_INFO, error):
              return True
      return False
