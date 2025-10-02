"""
Microsoft Defender XDR connector

Requirements
------------
pip install msal
Notice that it requires the "AdvancedHunting.Read.All" permission.

Description
-----------
This connector replaces the "microsoftsentinel" connector (https://learn.microsoft.com/en-us/azure/sentinel/move-to-defender).

Microsoft Defender provides a unified cybersecurity solution that integrates endpoint protection, cloud security, identity protection,
email security, threat intelligence, exposure management, and SIEM into a centralized platform powered by a modern data lake.

This connector allows querying Microsoft Defender XDR logs using KQL (Kusto Query Language).

Queries have to return a "Computer" column, corresponding to either a native "Computer" field, or a transformation.
If a transformation is required, it has to be part of the "query" field (not in the "columns" field).
You can define "Computer" by copying the value from another field: | project Computer = DstDvcHostname
You can also truncate the computer name to remove the domain: | project Computer = tostring(split(Computer, ".")[0])

Queries can use the {{StartTimeISO}} and {{EndTimeISO}} placeholders to define the time range for the query. For example, you can use the
following syntax to filter events from the last 14 days:

  let starttime = todatetime('{{StartTimeISO}}');
  let endtime = todatetime('{{EndTimeISO}}');
  let lookback = starttime - 14d;

To do
-----
- Sync rules not implemented yet.
- get_threats() not implemented yet.
"""

import requests
from msal import ConfidentialClientApplication
from connectors.utils import get_connector_conf, gzip_base64_urlencode, manage_analytic_error
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from urllib.parse import quote, unquote
import re
from notifications.utils import add_debug_notification
from datetime import date

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY, TENANT_ID, CLIENT_ID, CLIENT_SECRET, SYNC_RULES, QUERY_ERROR_INFO, \
            AUTHORITY, SCOPE, ENDPOINT, QUERY_LANGUAGE
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        QUERY_LANGUAGE = "Kusto Query Language (KQL)"
        PROXY = settings.PROXY
        TENANT_ID = get_connector_conf('microsoftdefender', 'TENANT_ID')
        CLIENT_ID = get_connector_conf('microsoftdefender', 'CLIENT_ID')
        CLIENT_SECRET = get_connector_conf('microsoftdefender', 'CLIENT_SECRET')
        SYNC_RULES = get_connector_conf('microsoftdefender', 'SYNC_RULES')
        QUERY_ERROR_INFO = get_connector_conf('microsoftdefender', 'QUERY_ERROR_INFO')

        # Microsoft Graph API endpoint
        AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
        SCOPE = ['https://graph.microsoft.com/.default']
        ENDPOINT = 'https://graph.microsoft.com/v1.0/security/runHuntingQuery'

        _globals_initialized = True


def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['requests', 'msal']

def query_language():
    """
    Return the query language used by SentinelOne.
    """
    init_globals()
    return QUERY_LANGUAGE

def authenticate():
    """
    Authenticate and get token
    :return: access token
    """
    init_globals()
    app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    token_response = app.acquire_token_for_client(scopes=SCOPE)
    access_token = token_response['access_token']
    return access_token

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
        access_token = authenticate()
    except:
        if debug or DEBUG:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Failed to connect to MS Defender. Check report for more info.")
        manage_analytic_error(analytic, f"Failed to connect to MS Defender while executing the analytic {analytic.name}.")
        return []

    # Define query and headers
    q = f'{analytic.query} | summarize count() by Computer'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    ### Define time range and body    
    # starttime and endtime are provided in the query
    if '{{StartTimeISO}}' in analytic.query and '{{EndTimeISO}}' in analytic.query:
        if from_date and to_date:
            # replace placeholders with provided dates
            q = q.replace('{{StartTimeISO}}', from_date)
            q = q.replace('{{EndTimeISO}}', to_date)
        else:
            today = date.today()
            yesterday = today - timedelta(days=1)
            # replace placeholders with provided dates
            q = q.replace('{{StartTimeISO}}', yesterday.isoformat())
            q = q.replace('{{EndTimeISO}}', today.isoformat())
        body = {
            'query': q,
        }
    # starttime and endtime are not provided in the query
    else:
        if from_date and to_date:
            timespan = f"{from_date.split('.')[0]}Z/{to_date.split('.')[0]}Z"
        else:
            # Default to the last 24 hours if no dates are provided
            timespan = 'P1D'

        body = {
            'query': q,
            'timespan': timespan,
        }
    if debug or DEBUG:
        print(f"Query: {q}")
 
    # Execute query
    try:
        response = requests.post(ENDPOINT, headers=headers, proxies=PROXY, json=body)
    except Exception as e:
        if debug or DEBUG:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Check report for more info.")
        manage_analytic_error(analytic, str(e))
        return "ERROR"

    # Handle response
    if response.status_code == 200:
        res = []
        results = response.json()
        if 'results' in results and len(results['results']) > 0:
            for row in results['results']:
                computer = row.get('Computer', '')
                count = row.get('count_', 0)
                res.append([computer, '', count, ''])
        return res
    else:
        if debug or DEBUG:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Check report for more info.")
        manage_analytic_error(analytic, f"Error: {response.status_code} - {response.text}")
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


def get_redirect_analytic_link(analytic, filter_date=None, endpoint_name=None):
    """
    Get the redirect link to run the analytic in MS Defender portal.
    :param analytic: Analytic object containing the query string and columns.
    :param filter_date: Date to filter the analytic by, in YYYY-MM-DD format (range will be date-date+1day).
    :param endpoint_name: Name of the endpoint to filter the analytic by.
    :return: String containing the redirect link for the analytic.
    """

    init_globals()

    q = analytic.query
    
    if '{{StartTimeISO}}' in q and '{{EndTimeISO}}' in q:
        if not filter_date:
            today = date.today()
            yesterday = today - timedelta(days=1)
            # replace placeholders with provided dates
            q = q.replace('{{StartTimeISO}}', yesterday.isoformat())
            q = q.replace('{{EndTimeISO}}', today.isoformat())
        else:
            # replace placeholders with provided dates
            start_date = datetime.strptime(filter_date, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            q = q.replace('{{StartTimeISO}}', start_date.isoformat())
            q = q.replace('{{EndTimeISO}}', end_date.isoformat())
    else:
        if not filter_date:
            # Default to 1 day
            timespan = "timeRangeId=day"
        else:
            # Convert date to ISO format and create a timespan (fromDate, toDate)
            # date format: 2025-07-01T00:00:00.000Z
            start_date = datetime.strptime(filter_date, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            timespan = f"fromDate={quote(start_date.isoformat(), safe='')}.000Z&toDate={quote(end_date.isoformat(), safe='')}.000Z"

    if endpoint_name:
        customized_query = f'{q} \n| where Computer startswith "{endpoint_name}"'
    else:
        customized_query = q

    # If the query field contains a "project" statement (used for a transformation),
    # we need to comment it out in order to avoid conflicts with the "columns" field.
    if "| project" in customized_query:
        customized_query = customized_query.replace("| project", "//| project")
    
    if analytic.columns:
        q = quote(f'{customized_query}\n{analytic.columns}')
    else:
        q = quote(customized_query)

    # Query needs to be encoded: utf-16le > gzip > base64 > URL encoding
    encoded_query = gzip_base64_urlencode(unquote(q), encoding='utf-16le')

    # Build the full URL
    if '{{StartTimeISO}}' in analytic.query and '{{EndTimeISO}}' in analytic.query:
        url = f"https://security.microsoft.com/v2/advanced-hunting?query={encoded_query}"
    else:
        url = f"https://security.microsoft.com/v2/advanced-hunting?query={encoded_query}&{timespan}"

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
