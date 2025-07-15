"""
SentinelOne connector
"""

from connectors.utils import get_connector_conf
from django.conf import settings
import logging
import requests
from time import sleep
from datetime import datetime, timedelta
from urllib.parse import quote, quote_plus
from connectors.utils import manage_analytic_error

# Get an instance of a logger
logger = logging.getLogger(__name__)

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY, DB_DATA_RETENTION, CAMPAIGN_MAX_HOSTS_THRESHOLD, DISABLE_RUN_DAILY_ON_ERROR
    global S1_URL, S1_TOKEN, S1_THREATS_URL, XDR_URL, XDR_PARAMS, SYNC_STAR_RULES, STAR_RULES_PREFIX, STAR_RULES_DEFAULTS
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        DB_DATA_RETENTION = settings.DB_DATA_RETENTION
        CAMPAIGN_MAX_HOSTS_THRESHOLD = settings.CAMPAIGN_MAX_HOSTS_THRESHOLD
        DISABLE_RUN_DAILY_ON_ERROR = settings.DISABLE_RUN_DAILY_ON_ERROR
        S1_URL = get_connector_conf('sentinelone', 'S1_URL')
        S1_TOKEN = get_connector_conf('sentinelone', 'S1_TOKEN')
        S1_THREATS_URL = get_connector_conf('sentinelone', 'S1_THREATS_URL')
        XDR_URL = get_connector_conf('sentinelone', 'XDR_URL')
        XDR_PARAMS = get_connector_conf('sentinelone', 'XDR_PARAMS')
        SYNC_STAR_RULES = get_connector_conf('sentinelone', 'SYNC_STAR_RULES')
        STAR_RULES_PREFIX = get_connector_conf('sentinelone', 'STAR_RULES_PREFIX')
        STAR_RULES_DEFAULTS = {
            'severity': get_connector_conf('sentinelone', 'STAR_RULES_DEFAULT_SEVERITY'), # Low|Medium|High|Critical
            'status': get_connector_conf('sentinelone', 'STAR_RULES_DEFAULT_STATUS'), # Active|Draft
            'expiration': get_connector_conf('sentinelone', 'STAR_RULES_DEFAULT_EXPIRATION'), # Integer. Will automatically consider expirationMode is "Temporary" and define an expiration (in days). Empty string to ignore
            'coolOffPeriod': get_connector_conf('sentinelone', 'STAR_RULES_DEFAULT_COOLOFFPERIOD'), # String. Cool Off Period (in minutes). Empty string to ignore
            'treatAsThreat': get_connector_conf('sentinelone', 'STAR_RULES_DEFAULT_TREATASTHREAT'), # Undefined(or empty)|Suspicious|Malicious.
            'networkQuarantine': get_connector_conf('sentinelone', 'STAR_RULES_DEFAULT_NETWORKQUARANTINE') # true|false
        }
        _globals_initialized = True


def query(analytic, from_date=None, to_date=None, debug=None):
    init_globals()
    
    # Use the global variable if not provided
    if debug is None:
        debug = DEBUG
    
    # Run analytic with filter for the last 24 hours by default, as the script is run every day, or from the given date range
    # hacklist is used instead of array_agg_distinct to get list of storylineid because
    # array_agg_distinct prevents the powerquery from executing without error
    q = f"{analytic.query} | group nb=count(), storylineid=hacklist(src.process.storyline.id) by endpoint.name, site.name"
    
    if not from_date:
        # if date range is not provided, we use the last 24 hours
        to_date = datetime.combine(datetime.today(), datetime.min.time())
        from_date = (to_date - timedelta(hours=24)).isoformat()
        to_date = to_date.isoformat()
    
    body = {
        'fromDate': from_date,
        'query': q,
        'toDate': to_date,
        'limit': CAMPAIGN_MAX_HOSTS_THRESHOLD
    }
    
    if debug or DEBUG:
        print('*** RUNNING QUERY {}: {}'.format(analytic.name, analytic.query))
        print('*** BODY: {}'.format(body))
        
    try:
        r = requests.post(f'{S1_URL}/web/api/v2.1/dv/events/pq',
            json=body,
            headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
            proxies=PROXY)

        query_id = r.json()['data']['queryId']
        status = r.json()['data']['status']

        # Ping PowerQuery every second, until it is complete (unless you do that, the PQ will be cancelled)
        while status == 'RUNNING':
            r = requests.get(f'{S1_URL}/web/api/v2.1/dv/events/pq-ping',
                params = {"queryId": query_id},
                headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
                proxies=PROXY)
                
            status = r.json()['data']['status']
            progress = r.json()['data']['progress']
            
            if debug or DEBUG:
                print('PROGRESS: {}'.format(progress))
            
            sleep(1)

                
        if debug or DEBUG:
            print('***DATA (JSON): {}'.format(r.json()))
        
        return r.json()['data']['data']
    
    
    except:
        if debug or DEBUG:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Check report for more info.")
        
        manage_analytic_error(analytic, r.text)

        return []

def need_to_sync_rule():
    """
    Check if the rule needs to be synced with SentinelOne.
    This is determined by the SYNC_STAR_RULES setting.
    """
    init_globals()
    return SYNC_STAR_RULES

def build_rule_body(analytic):
    """
    Build the body for the SentinelOne rule query.
    Used for rule creation and update.
    :param analytic: Analytic object corresponding to the analytic.
    :return: Dictionary containing the body for the rule query.
    """
    
    init_globals()
    body = {
        "data": {
            "queryLang": "2.0",
            "severity": STAR_RULES_DEFAULTS['severity'],
            "description": "Rule Sync from DeepHunter",
            "s1ql": analytic.query,
            "name": f"{STAR_RULES_PREFIX}{analytic.name}",
            "queryType": "events",
            "status": STAR_RULES_DEFAULTS['status']
        },
        "filter": {
            "tenant": "true" # filter "tenant=true" is to apply rule to scope "global"
        }
    }

    # Expiration
    if STAR_RULES_DEFAULTS['expiration']:
        # if expiration is set in settings, it means mode is Temporary.
        # We compute the target date
        body['data']['expirationMode'] = 'Temporary'
        body['data']['expiration'] = (datetime.utcnow()+timedelta(days=int(STAR_RULES_DEFAULTS['expiration']))).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
    else:
        # Empty string or 0 value set for expiration in settings means Permanent
        body['data']['expirationMode'] = 'Permanent'
    
    # Cool Off Period
    if STAR_RULES_DEFAULTS['coolOffPeriod']:
        body['data']['coolOffSettings'] = {"renotifyMinutes": int(STAR_RULES_DEFAULTS['coolOffPeriod'])}
    
    # treatAsThreat
    if STAR_RULES_DEFAULTS['treatAsThreat'] == 'Suspicious' or STAR_RULES_DEFAULTS['treatAsThreat'] == 'Malicious':
        body['data']['treatAsThreat'] = STAR_RULES_DEFAULTS['treatAsThreat']
    
    # networkQuarantine
    if STAR_RULES_DEFAULTS['networkQuarantine'].lower() == 'true':
        body['data']['networkQuarantine'] = 'true'

    return body

def create_rule(analytic):
    """
    Create a STAR rule in SentinelOne based on the query field of the analytic passed as argument.
    :param analytic: Analytic object corresponding to the analytic.
    :return: JSON object containing the response from SentinelOne API.
    """
    init_globals()
    body = build_rule_body(analytic)
    r = requests.post(f'{S1_URL}/web/api/v2.1/cloud-detection/rules',
        json=body,
        headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
        proxies=PROXY
        )
    return r.json()

def update_rule(analytic):
    """
    Update a STAR rule in SentinelOne based on the query field of the analytic passed as argument.
    :param analytic: Analytic object corresponding to the analytic.
    :return: JSON object containing the response from SentinelOne API.
    """

    init_globals()
    # check if STAR rule already exists (STAR rule flag was previously set)
    r = requests.get(f'{S1_URL}/web/api/v2.1/cloud-detection/rules?name__contains={STAR_RULES_PREFIX}{analytic.name}',
        headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
        proxies=PROXY
        )
    if r.status_code == 200 and 'data' in r.json():
        # if it exists, update it, but preserve severity and expiration              
        rule_id = r.json()['data'][0]['id']
        severity = r.json()['data'][0]['severity']
        expirationMode = r.json()['data'][0]['expirationMode']

        if expirationMode == 'Permanent':
            body_update = {
                "data": {
                    "queryLang": "2.0",
                    "severity": severity,
                    "s1ql": analytic.query,
                    "name": f"{STAR_RULES_PREFIX}{analytic.name}",
                    "queryType": "events",
                    "expirationMode": "Permanent",
                    "status": STAR_RULES_DEFAULTS['status']
                },
                "filter": {
                    "tenant": "true"
                }
            }
        else:
            body_update = {
                "data": {
                    "queryLang": "2.0",
                    "severity": severity,
                    "s1ql": analytic.query,
                    "name": f"{STAR_RULES_PREFIX}{analytic.name}",
                    "queryType": "events",
                    "expirationMode": "Temporary",
                    "expiration": r.json()['data'][0]['expiration'],
                    "status": STAR_RULES_DEFAULTS['status']
                },
                "filter": {
                    "tenant": "true"
                }
            }
            
        r = requests.put(f'{S1_URL}/web/api/v2.1/cloud-detection/rules/{rule_id}',
            json=body_update,
            headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
            proxies=PROXY
            )
    else:
        # if it does not exist (STAR rule flag was not set), create it
        body_new = build_rule_body(analytic)
        r = requests.post(f'{S1_URL}/web/api/v2.1/cloud-detection/rules',
            json=body_new,
            headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
            proxies=PROXY
            )

    return r.json()

def delete_rule(analytic):
    """
    Delete a STAR rule in SentinelOne based on the query field of the analytic passed as argument.
    
    :param analytic: Analytic object corresponding to the analytic.
    :return: None
    """
    init_globals()
    body = {
        "filter": {
            "name__contains": f"{STAR_RULES_PREFIX}{analytic.name}"
        }
    }
    r = requests.delete(f'{S1_URL}/web/api/v2.1/cloud-detection/rules',
        json=body,
        headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
        proxies=PROXY
        )

def get_threats(hostname, created_at):
    """
    Get threats from SentinelOne for a specific hostname and created_at date.
    :param hostname: Hostname of the machine to retrieve threats for.
    :param created_at: Date in ISO format to filter threats created after this date.
    :return: List of threats (array) or None if not found.
    """
    init_globals()
    r = requests.get(
        f'{S1_URL}/web/api/v2.1/threats?computerName__contains={hostname}&createdAt__gte={created_at}',
        params = {"limit": 100},
        headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
        proxies=PROXY
        )
    return r.json()['data'] if r.status_code == 200 and r.json()['data'] else None

def get_machine_details(hostname):
    """
    Get machine details from SentinelOne
    :param hostname: Hostname of the machine to retrieve details for.
    :return: Dictionary containing machine details or None if not found.
    """
    init_globals()
    r = requests.get(
        '{}/web/api/v2.1/agents?computerName={}'.format(S1_URL, hostname),
        headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
        proxies=PROXY
        )
    return r.json()['data'][0] if r.status_code == 200 and r.json()['data'] else None

def get_last_logged_in_user(agent_id):
    """
    Get machine owner from SentinelOne
    :param agent_id: S1 Agent ID of the machine to retrieve last logged in user from.
    :return: String containing the machine owner or None if not found.
    """
    init_globals()
    r = requests.get(
        '{}/web/api/v2.1/agents?ids={}'.format(S1_URL, agent_id),
        headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
        proxies=PROXY
        )
    if r.status_code == 200 and r.json()['data']:
        return r.json()['data'][0]['lastLoggedInUserName']
    return None

def get_applications(agent_id):
    """
    Get list of installed applications from SentinelOne for a specific agent ID.
    :param agent_id: S1 Agent ID of the machine to retrieve applications for.
    :return: List of applications (array) or None if not found.
    """
    init_globals()
    r = requests.get(
        f'{S1_URL}/web/api/v2.1/agents/applications?ids={agent_id}',
        headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
        proxies=PROXY
        )
    return r.json()['data'] if r.status_code == 200 and r.json()['data'] else None

def get_redirect_analytic_link(analytic, date=None, endpoint_name=None):
    """
    Get the redirect link to run the analytic in SentinelOne.
    
    :param endpoint_name: Name of the endpoint to filter the analytic by.
    :param analytic: Analytic object containing the query string and columns.
    :param date: Date to filter the analytic by, in ISO format (range will be date-date+1day).
    :return: String containing the redirect link for the analytic.
    """
    init_globals()
    if not date:
        date = (datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
    
    if endpoint_name:
        customized_query = f"{analytic.query} \n| filter endpoint.name='{endpoint_name}'"
    else:
        customized_query = analytic.query

    if analytic.columns:
        q = quote(f'{customized_query}\n{analytic.columns}')
    else:
        q = quote(customized_query)
    
    return '{}/query?filter={}&startTime={}&endTime=%2B1+day&{}'.format(XDR_URL, q.replace('%0D', ''), date, XDR_PARAMS)

def get_redirect_storyline_link(storyline_ids, date):
    """
    Get the redirect link to run the storyline in SentinelOne.
    
    :param storyline_id: ID (or list of IDs) of the storyline(s).
    :param date: Date to filter the analytic by, in ISO format (range will be date-date+1day).
    :return: String containing the redirect link for the storyline.
    """
    init_globals()
    if ',' in storyline_ids:
        filter = "src.process.storyline.id in {} or tgt.process.storyline.id in {}".format(tuple(storyline_ids.split(',')), tuple(storyline_ids.split(',')))
    else:
        filter = f"src.process.storyline.id = '{storyline_ids}' or tgt.process.storyline.id = '{storyline_ids}'"
    
    return '{}/events?filter={}&startTime={}&endTime=%2B1+day&{}'.format(XDR_URL, quote_plus(filter), date, XDR_PARAMS)

def get_network_connections(storyline_id, endpoint_name, timerange):
    """
    Get network connections for a specific storyline ID and endpoint name.
    
    :param storyline_id: ID of the storyline to retrieve network connections for.
    :param endpoint_name: Name of the endpoint to filter the analytic by.
    :param timerange: Time range in hours to filter the analytic by.
    :return: List of network connections (array) or None if not found.
    """
    
    init_globals()
    query = "| join ("
    if endpoint_name:
        query += "endpoint.name = '{}' and ".format(endpoint_name)
    if storyline_id:
        query += "src.process.storyline.id = '{}' and ".format(storyline_id)
    query += """
event.category = 'ip' 
and dst.ip.address != '127.0.0.1' 
| group nbevents=count(), dstports=hacklist(dst.port.number) by dst.ip.address 
), ( 
| group nbhosts=estimate_distinct(endpoint.name) by dst.ip.address 
) on dst.ip.address 
| sort nbhosts
"""
    body = {
        'fromDate': (datetime.now() - timedelta(hours=timerange)).isoformat(),
        'query': query,
        'toDate': datetime.now().isoformat(),
        'limit': 100
    }
            
    r = requests.post('{}/web/api/v2.1/dv/events/pq'.format(S1_URL),
        json=body,
        headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
        proxies=PROXY)

    try:
        query_id = r.json()['data']['queryId']
        status = r.json()['data']['status']
    
        # Ping PowerQuery every second, until it is complete (unless you do that, the PowerQuery will be cancelled)
        while status == 'RUNNING':
            r = requests.get('{}/web/api/v2.1/dv/events/pq-ping'.format(S1_URL),
                params = {"queryId": query_id},
                headers={'Authorization': 'ApiToken:{}'.format(S1_TOKEN)},
                proxies=PROXY)
                
            status = r.json()['data']['status']
            progress = r.json()['data']['progress']
            
            sleep(1)

        return r.json()['data'] if r.status_code == 200 and r.json()['data'] else None
    
    except:
        return None


def get_token_expiration_date():
    """
    Get the expiration date of the SentinelOne API token.
    :return: String containing the expiration date in ISO format or None if not found.
    """
    init_globals()
    r = requests.post(f'{S1_URL}/web/api/v2.1/users/api-token-details',
        headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
        json={ "data": { "apiToken": S1_TOKEN } },
        proxies=PROXY)
    
    if r.status_code == 200 and 'data' in r.json():
        return r.json()['data']['expiresAt']
    else:
        if DEBUG:
            print(f"[ ERROR ] Failed to retrieve token expiration date: {r.text}")
        logger.error(f"Failed to retrieve token expiration date: {r.text}")
        return None
