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

The python file should be stored in the `plugins` folder. It should contain at least mandatory methods. You can also add additional methods to enhance the functionality of your plugin.

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

