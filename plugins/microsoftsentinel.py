"""
Microsoft Sentine connector

Requirements
------------
pip install azure-identity azure-monitor-query

Description
-----------
This connector allows querying Microsoft Sentinel logs using KQL (Kusto Query Language).
Queries have to return a "Computer" column, corresponding to either a native "Computer" field, or a transformation.
If a transformation is required, it has to be part of the "query" field (not in the "columns" field).
You can define "Computer" by copying the value from another field: | project Computer = DstDvcHostname
You can also truncate the computer name to remove the domain: | project Computer = tostring(split(Computer, ".")[0])

To do
-----
- Sync rules not implemented yet.
- get_threats() not implemented yet.
"""

from azure.identity import ClientSecretCredential
from azure.monitor.query import LogsQueryClient
from azure.monitor.query import LogsQueryStatus
from connectors.utils import get_connector_conf, gzip_base64_urlencode, manage_analytic_error
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote
import re
from notifications.utils import add_debug_notification

_globals_initialized = False
def init_globals():
    global DEBUG, TENANT_ID, CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID, WORKSPACE_ID, \
            WORKSPACE_NAME, RESOURCE_GROUP, SYNC_RULES, QUERY_ERROR_INFO
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        TENANT_ID = get_connector_conf('microsoftsentinel', 'TENANT_ID')
        CLIENT_ID = get_connector_conf('microsoftsentinel', 'CLIENT_ID')
        CLIENT_SECRET = get_connector_conf('microsoftsentinel', 'CLIENT_SECRET')
        SUBSCRIPTION_ID = get_connector_conf('microsoftsentinel', 'SUBSCRIPTION_ID')
        WORKSPACE_ID = get_connector_conf('microsoftsentinel', 'WORKSPACE_ID')
        WORKSPACE_NAME = get_connector_conf('microsoftsentinel', 'WORKSPACE_NAME').lower()
        RESOURCE_GROUP = get_connector_conf('microsoftsentinel', 'RESOURCE_GROUP')
        SYNC_RULES = get_connector_conf('microsoftsentinel', 'SYNC_RULES')
        QUERY_ERROR_INFO = get_connector_conf('microsoftsentinel', 'QUERY_ERROR_INFO')
        _globals_initialized = True


def authenticate():
    init_globals()
    credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    client = LogsQueryClient(credential)
    return client


def query(analytic, from_date=None, to_date=None, debug=None):
    """
    API calls to Microsoft Sentinel to query logs. Used by the "campaign" daily cron, and the "regenerate stats" script
    :param analytic: Analytic object corresponding to the threat hunting analytic.
    :param from_date: Optional start date for the query. Date received in isoformat.
    :param to_date: Optional end date for the query. Date received in isoformat.
    :return: The result of the query (array with 4 fields: endpoint.name, NULL, number of hits, NULL), or "ERROR" if the query failed.
    """
    
    init_globals()

    # Authentication
    try:
        client = authenticate()
    except:
        if debug or DEBUG:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Failed to connect to MS Sentinel. Check report for more info.")        
        manage_analytic_error(analytic, f"Failed to connect to MS Sentinel while executing the analytic {analytic.name}.")
        return []


    if from_date and to_date:
        start_date = datetime.fromisoformat(from_date)
        start_date_utc = start_date.replace(tzinfo=timezone.utc)
        end_date = datetime.fromisoformat(to_date)
        end_date_utc = end_date.replace(tzinfo=timezone.utc)
        timespan = (start_date_utc, end_date_utc)
    else:
        # Default to the last 24 hours if no dates are provided
        timespan = timedelta(hours=24)


    q = f'{analytic.query} | summarize count() by Computer'
    if debug or DEBUG:
        print(f"Query: {q}")
    
    try:
        # Execute query
        response = client.query_workspace(
            workspace_id=WORKSPACE_ID,
            query=q,
            timespan=timespan
        )
    except Exception as e:
        if debug or DEBUG:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Check report for more info.")
        manage_analytic_error(analytic, e.message)
        return "ERROR"

    # Handle response
    if response.status == LogsQueryStatus.SUCCESS:
        res = []
        for table in response.tables:
            for row in table.rows:
                res.append([row[0], '', row[1], ''])
        return res
    else:
        if debug or DEBUG:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Check report for more info.")
        manage_analytic_error(analytic, response.error)
        return "ERROR"

def need_to_sync_rule():
    """
    Check if the rule needs to be synced with Microsoft Sentinel.
    This is determined by the SYNC_RULES setting.
    """
    init_globals()
    return SYNC_RULES

def create_rule(analytic):
    """
    TO BE COMPLETED
    """
    init_globals()
    return False

def update_rule(analytic):
    """
    TO BE COMPLETED
    """
    init_globals()
    return False

def delete_rule(analytic):
    """
    TO BE COMPLETED
    """
    init_globals()
    return False


def get_redirect_analytic_link(analytic, date=None, endpoint_name=None):

    ### pre-filling the KQL query field via URL in the Microsoft Sentinel LogsBlade.
    ###

    init_globals()
    if not date:
        timespan = "P1D"  # Default to 1 day
    else:
        # Convert date to ISO format and create a timespan
        # example: /2025-07-01T00%3A00%3A00.000Z%2F2025-07-08T12%3A00%3A00.000Z/
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        timespan = quote(f"{start_date.isoformat()}Z/{end_date.isoformat()}Z", safe='')
    
    if endpoint_name:
        customized_query = f'{analytic.query} \n| where Computer startswith "{endpoint_name}"'
    else:
        customized_query = analytic.query

    # If the query field contains a "project" statement (used for a transformation),
    # we need to comment it out in order to avoid conflicts with the "columns" field.
    if "| project" in customized_query:
        customized_query = customized_query.replace("| project", "//| project")
    
    if analytic.columns:
        q = quote(f'{customized_query}\n{analytic.columns}')
    else:
        q = quote(customized_query)

    # Query needs to be encoded using gzip and base64 URL encoding
    encoded_query = gzip_base64_urlencode(unquote(q))

    # Build the full URL
    url = (
        f"https://portal.azure.com#@{TENANT_ID}/blade/Microsoft_OperationsManagementSuite_Workspace/Logs.ReactView/resourceId/"
        f"%2Fsubscriptions%2F{SUBSCRIPTION_ID}%2FresourceGroups%2F{RESOURCE_GROUP}%2Fproviders%2FMicrosoft.OperationalInsights"
        f"%2Fworkspaces%2F{WORKSPACE_NAME}/source/LogsBlade.AnalyticsShareLinkToQuery/q/{encoded_query}/timespan/{timespan}/limit/100000"
    )

    return url

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
