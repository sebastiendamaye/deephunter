"""
Microsoft Sentine connector

Requirements:
pip install azure-identity azure-monitor-query

To do:
Sync rules not implemented yet.
"""

from azure.identity import ClientSecretCredential
from azure.monitor.query import LogsQueryClient
from azure.monitor.query import LogsQueryStatus
from connectors.utils import get_connector_conf, gzip_base64_urlencode, manage_query_error
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Set to True for debugging purposes
DEBUG = True

# Retrieve connector settings from the database
TENANT_ID = get_connector_conf('microsoftsentinel', 'TENANT_ID')
CLIENT_ID = get_connector_conf('microsoftsentinel', 'CLIENT_ID')
CLIENT_SECRET = get_connector_conf('microsoftsentinel', 'CLIENT_SECRET')
SUBSCRIPTION_ID = get_connector_conf('microsoftsentinel', 'SUBSCRIPTION_ID')
WORKSPACE_ID = get_connector_conf('microsoftsentinel', 'WORKSPACE_ID')
WORKSPACE_NAME = get_connector_conf('microsoftsentinel', 'WORKSPACE_NAME').lower()
RESOURCE_GROUP = get_connector_conf('microsoftsentinel', 'RESOURCE_GROUP')
SYNC_RULES = get_connector_conf('microsoftsentinel', 'SYNC_RULES')

def authenticate():
    credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    client = LogsQueryClient(credential)
    return client


def query(query, from_date=None, to_date=None):
    """
    API calls to Microsoft Sentinel to query logs. Used by the "campaign" daily cron, and the "regenerate stats" script
    :param query: Query object corresponding to the threat hunting analytic.
    :param from_date: Optional start date for the query. Date received in isoformat.
    :param to_date: Optional end date for the query. Date received in isoformat.
    :return: The result of the query (array with 4 fields: endpoint.name, NULL, number of hits, NULL), or None if the query failed.
    """
    
    if from_date and to_date:
        start_date = datetime.fromisoformat(from_date)
        start_date_utc = start_date.replace(tzinfo=timezone.utc)
        end_date = datetime.fromisoformat(to_date)
        end_date_utc = end_date.replace(tzinfo=timezone.utc)
        timespan = (start_date_utc, end_date_utc)
    else:
        # Default to the last 24 hours if no dates are provided
        timespan = timedelta(hours=24)

    client = authenticate()
    # KQL query
    q = f'{query.query} | summarize count() by Computer = tostring(split(Computer, ".")[0])'

    # Execute query
    response = client.query_workspace(
        workspace_id=WORKSPACE_ID,
        query=q,
        timespan=timespan
    )

    # Handle response
    if response.status == LogsQueryStatus.SUCCESS:
        res = []
        for table in response.tables:
            for row in table.rows:
                res.append([row[0], '', row[1], ''])
        return res
    else:
        if DEBUG:
            logger.error(f"Query failed: {response.error}")
        manage_query_error(query, response.error)
        return None

def need_to_sync_rule():
    """
    Check if the rule needs to be synced with Microsoft Sentinel.
    This is determined by the SYNC_RULES setting.
    """
    return SYNC_RULES

def create_rule(query):
    """
    TO BE COMPLETED
    """
    return False

def update_rule(query):
    """
    TO BE COMPLETED
    """
    return False

def delete_rule(query):
    """
    TO BE COMPLETED
    """
    return False


def get_redirect_query_link(query, date=None, endpoint_name=None):

    ### pre-filling the KQL query field via URL in the Microsoft Sentinel LogsBlade.
    ###

    if not date:
        timespan = "P1D"  # Default to 1 day
    else:
        # Convert date to ISO format and create a timespan
        # example: /2025-07-01T00%3A00%3A00.000Z%2F2025-07-08T12%3A00%3A00.000Z/
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        timespan = quote(f"{start_date.isoformat()}Z/{end_date.isoformat()}Z", safe='')
    
    if endpoint_name:
        customized_query = f"{query.query} \n| where Computer=='{endpoint_name}'"
    else:
        customized_query = query.query

    if query.columns:
        q = quote(f'{customized_query}\n{query.columns}')
    else:
        q = quote(customized_query)

    encoded_query = gzip_base64_urlencode(unquote(q))

    # Build the full URL
    url = (
        f"https://portal.azure.com#@{TENANT_ID}/blade/Microsoft_OperationsManagementSuite_Workspace/Logs.ReactView/resourceId/"
        f"%2Fsubscriptions%2F{SUBSCRIPTION_ID}%2FresourceGroups%2F{RESOURCE_GROUP}%2Fproviders%2FMicrosoft.OperationalInsights"
        f"%2Fworkspaces%2F{WORKSPACE_NAME}/source/LogsBlade.AnalyticsShareLinkToQuery/q/{encoded_query}/timespan/{timespan}/limit/100000"
    )

    return url
