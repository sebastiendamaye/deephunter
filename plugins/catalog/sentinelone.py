"""
SentinelOne connector
"""

from connectors.utils import get_connector_conf
from django.conf import settings
import requests
import re
from time import sleep, monotonic
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, quote_plus
from connectors.utils import manage_analytic_error
from notifications.utils import add_error_notification

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY, DB_DATA_RETENTION, CAMPAIGN_MAX_HOSTS_THRESHOLD, \
            S1_URL, S1_TOKEN, S1_ACCOUNT_IDS, S1_THREATS_URL, XDR_URL, XDR_PARAMS, SYNC_STAR_RULES, STAR_RULES_PREFIX, \
            STAR_RULES_DEFAULTS, QUERY_ERROR_INFO, QUERY_LANGUAGE
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        QUERY_LANGUAGE = "SentinelOne PowerQuery S1QL 2.0"
        PROXY = settings.PROXY
        DB_DATA_RETENTION = settings.DB_DATA_RETENTION
        CAMPAIGN_MAX_HOSTS_THRESHOLD = settings.CAMPAIGN_MAX_HOSTS_THRESHOLD
        S1_URL = get_connector_conf('sentinelone', 'S1_URL')
        S1_TOKEN = get_connector_conf('sentinelone', 'S1_TOKEN')
        # Optional. Comma-separated account IDs to scope LRQ queries. Empty/missing = whole tenant
        S1_ACCOUNT_IDS = get_connector_conf('sentinelone', 'S1_ACCOUNT_IDS')
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
        QUERY_ERROR_INFO = get_connector_conf('sentinelone', 'QUERY_ERROR_INFO')
        _globals_initialized = True

def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['requests']

def query_language():
    """
    Return the query language used by SentinelOne.
    """
    init_globals()
    return QUERY_LANGUAGE

LRQ_POLL_INTERVAL = 1   # seconds. A LRQ query expires 30s after the last poll
LRQ_TIMEOUT = 900       # seconds. Cancel the query if not complete after 15 minutes
LRQ_REQUEST_TIMEOUT = 30    # seconds. Timeout of each HTTP call
LRQ_RETRY_DELAYS = [1, 2, 4, 8]    # seconds. Total stays below the 30s expiration of a LRQ query
LRQ_RETRY_STATUSES = {429, 500, 502, 503, 504}
LRQ_MAX_SUBMISSIONS = 3    # Resubmit a query up to 2 times if it expires server-side (404 on poll)

class PowerQueryError(Exception):
    pass

def _lrq_headers(forward_tag=None):
    # LRQ expects the same token as the mgmt API, but with the "Bearer" prefix
    headers = {'Authorization': f'Bearer {S1_TOKEN}'}
    if forward_tag:
        headers['X-Dataset-Query-Forward-Tag'] = forward_tag
    return headers

def _lrq_request(method, url, **kwargs):
    """
    HTTP call to the LRQ API, retried on transient errors: rate limit (429), gateway errors
    (e.g., 503 "upstream connect error or disconnect/reset before headers") and connection errors.
    :return: the last response. Raise the last connection error if all attempts failed.
    """
    for attempt, delay in enumerate(LRQ_RETRY_DELAYS + [None], start=1):
        try:
            r = requests.request(method, url, proxies=PROXY, timeout=LRQ_REQUEST_TIMEOUT, **kwargs)
            if r.status_code not in LRQ_RETRY_STATUSES or delay is None:
                return r
            error = f'HTTP {r.status_code}: {r.text}'
        except (requests.ConnectionError, requests.Timeout) as e:
            if delay is None:
                raise
            error = repr(e)
        if DEBUG:
            print(f'[ WARNING ] LRQ {method} attempt {attempt} failed ({error}). Retrying in {delay}s')
        sleep(delay)

def _to_utc_iso(d):
    # LRQ expects ISO-8601 with a "Z" suffix. Naive dates are considered UTC
    if isinstance(d, str):
        d = datetime.fromisoformat(d)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def _hacklist_to_str(value):
    # Keep the "[a,b,c]" string format returned by the former dv/events/pq endpoint
    if isinstance(value, list):
        return '[{}]'.format(','.join(str(v) for v in value))
    return value

def run_powerquery(q, from_date, to_date, debug=False):
    """
    Run a PowerQuery with the Long Running Query (LRQ) API.
    Replaces /web/api/v2.1/dv/events/pq (deprecated on Feb 15, 2027).
    :param q: PowerQuery string.
    :param from_date: Start date (datetime or ISO string).
    :param to_date: End date (datetime or ISO string).
    :return: tuple (columns, values): list of column names, list of rows.
    :raise PowerQueryError: with the API response text if the query fails.
    """
    init_globals()

    body = {
        'queryType': 'PQ',
        'startTime': _to_utc_iso(from_date),
        'endTime': _to_utc_iso(to_date),
        'queryPriority': 'HIGH',
        'pq': {'query': q, 'resultType': 'TABLE'}
    }
    if S1_ACCOUNT_IDS:
        body['tenant'] = False
        body['accountIds'] = [i.strip() for i in S1_ACCOUNT_IDS.split(',') if i.strip()]
    else:
        body['tenant'] = True

    if debug:
        print(f'*** LRQ BODY: {body}')

    deadline = monotonic() + LRQ_TIMEOUT
    for submission in range(1, LRQ_MAX_SUBMISSIONS + 1):
        r = _lrq_request('POST', f'{S1_URL}/sdl/v2/api/queries',
            json=body,
            headers=_lrq_headers())
        if r.status_code >= 400:
            raise PowerQueryError(r.text)

        query_id = r.json()['id']
        # Must be sent back on every GET/DELETE (routes to the shard holding the query)
        headers = _lrq_headers(r.headers.get('X-Dataset-Query-Forward-Tag'))

        expired = False
        try:
            steps_seen = 0
            while True:
                if monotonic() > deadline:
                    raise PowerQueryError(f'LRQ query {query_id} not complete after {LRQ_TIMEOUT}s')

                r = _lrq_request('GET', f'{S1_URL}/sdl/v2/api/queries/{query_id}',
                    params={'lastStepSeen': steps_seen},
                    headers=headers)
                # 404 "Requested token=<id> not found": the query expired server-side (not polled
                # within 30s, e.g., after a slow or timed out poll). Resubmit it
                if r.status_code == 404 and submission < LRQ_MAX_SUBMISSIONS:
                    expired = True
                    break
                if r.status_code >= 400:
                    raise PowerQueryError(r.text)

                result = r.json()
                steps_seen = result.get('stepsCompleted') or 0
                steps_total = result.get('stepsTotal') or 0

                if debug:
                    print(f'PROGRESS: {steps_seen}/{steps_total}')

                if steps_total > 0 and steps_seen >= steps_total:
                    break

                sleep(LRQ_POLL_INTERVAL)
        finally:
            # Always cancel the query (even on success) to release server-side resources
            try:
                requests.delete(f'{S1_URL}/sdl/v2/api/queries/{query_id}',
                    headers=headers,
                    proxies=PROXY,
                    timeout=LRQ_REQUEST_TIMEOUT)
            except requests.RequestException:
                pass

        if not expired:
            break
        if debug:
            print(f'[ WARNING ] LRQ query {query_id} expired (submission {submission}). Resubmitting')

    data = result.get('data') or {}
    columns = [c.get('name') if isinstance(c, dict) else c for c in data.get('columns') or []]
    values = data.get('values') or []

    if debug:
        print(f'***COLUMNS: {columns}')
        print(f'***VALUES: {values}')

    return columns, values

def query(analytic, from_date=None, to_date=None, debug=None):
    init_globals()
    
    # Use the global variable if not provided
    if debug is None:
        debug = DEBUG
    
    # Run analytic with filter for the last 24 hours by default, as the script is run every day, or from the given date range
    # hacklist is used instead of array_agg_distinct to get list of storylineid because
    # array_agg_distinct prevents the powerquery from executing without error
    # LRQ has no "limit" body parameter, so the limit is part of the query
    q = f"{analytic.query} | group nb=count(), storylineid=hacklist(src.process.storyline.id) by endpoint.name, site.name | limit {CAMPAIGN_MAX_HOSTS_THRESHOLD}"
    
    if not from_date:
        # if date range is not provided, we use the last 24 hours
        to_date = datetime.combine(datetime.today(), datetime.min.time())
        from_date = (to_date - timedelta(hours=24)).isoformat()
        to_date = to_date.isoformat()
    
    if debug:
        print('*** RUNNING QUERY {}: {}'.format(analytic.name, analytic.query))
        
    try:
        columns, values = run_powerquery(q, from_date, to_date, debug)

        # Callers expect rows as [endpoint.name, site.name, nb, storylineid]
        idx = [columns.index(c) for c in ('endpoint.name', 'site.name', 'nb', 'storylineid')]
        data = []
        for v in values:
            row = [v[i] for i in idx]
            row[3] = _hacklist_to_str(row[3])
            data.append(row)

        return data
    
    except Exception as e:
        if debug:
            print(f"[ ERROR ] Analytic {analytic.name} failed. Check report for more info.")
        
        manage_analytic_error(analytic, str(e))

        return "ERROR"

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
            "s1ql": analytic.query.replace('\r', ' ').replace('\n', ' '), # unless you remove CR/NL, error: Wrong query Query cannot contain newlines
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
        body['data']['expiration'] = (datetime.now()+timedelta(days=int(STAR_RULES_DEFAULTS['expiration']))).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
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
                    "s1ql": analytic.query.replace('\r', ' ').replace('\n', ' '), # unless you remove CR/NL, error: Wrong query Query cannot contain newlines
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
                    "s1ql": analytic.query.replace('\r', ' ').replace('\n', ' '), # unless you remove CR/NL, error: Wrong query Query cannot contain newlines
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

def get_threats(hostname, sincedate):
    """
    Get threats from SentinelOne for a specific hostname and created_at date.
    :param hostname: Hostname of the machine to retrieve threats for.
    :param sincedate: Date in ISO format to filter threats created after this date.
    :return: List of threats (array) or None if not found.
    """
    init_globals()
    r = requests.get(
        f'{S1_URL}/web/api/v2.1/threats?computerName__contains={hostname}&createdAt__gte={sincedate}',
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

def get_redirect_analytic_link(analytic, filter_date=None, endpoint_name=None):
    """
    Get the redirect link to run the analytic in SentinelOne.    
    :param analytic: Analytic object containing the query string and columns.
    :param date: Date to filter the analytic by, in YYYY-MM-DD format (range will be date-date+1day).
    :param endpoint_name: Name of the endpoint to filter the analytic by.
    :return: String containing the redirect link for the analytic.
    """
    init_globals()
    if not filter_date:
        filter_date = (datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
    
    if endpoint_name:
        customized_query = f"{analytic.query} \n| filter endpoint.name='{endpoint_name}'"
    else:
        customized_query = analytic.query

    if analytic.columns:
        q = quote(f'{customized_query}\n{analytic.columns}')
    else:
        q = quote(customized_query)
    
    return '{}/query?filter={}&startTime={}&endTime=%2B1+day&{}'.format(XDR_URL, q.replace('%0D', ''), filter_date, XDR_PARAMS)

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

def get_network_connections(endpoint_name, timerange, storyline_id=None):
    """
    Get network connections for a specific storyline ID and endpoint name.
    
    :param endpoint_name: Name of the endpoint to filter the analytic by.
    :param timerange: Time range in hours to filter the analytic by.
    :param storyline_id: storyline ID to retrieve network connections for (only relevant for SentinelOne).
    :return: List of network connections ([dst_ip, nb_events, dst_ports_separator_hash_sign, nb_hosts_same_dstip]) or None if not found.
    """

    init_globals()

    query = "| join ("
    if endpoint_name:
        query += f"endpoint.name = '{endpoint_name}' and "
    if storyline_id:
        query += f"src.process.storyline.id = '{storyline_id}' and "
    query += """
event.category = 'ip' 
and dst.ip.address != '127.0.0.1' 
| group nbevents=count(), dstports=hacklist(dst.port.number) by dst.ip.address 
), ( 
| group nbhosts=estimate_distinct(endpoint.name) by dst.ip.address 
) on dst.ip.address 
| sort nbhosts
"""
    query += "| limit 100"

    try:
        columns, values = run_powerquery(query,
            datetime.now() - timedelta(hours=timerange),
            datetime.now())
        if not values:
            return None

        # Callers expect rows as [dst.ip.address, nbevents, dstports, nbhosts]
        idx = [columns.index(c) for c in ('dst.ip.address', 'nbevents', 'dstports', 'nbhosts')]
        return [[_hacklist_to_str(v[i]) for i in idx] for v in values]

    except Exception:
        return None


def get_token_expiration():
    """
    Get the expiration (in days) of the SentinelOne API token.
    :return: integer (number of days) or None.
    """

    init_globals()
    try:
        r = requests.post(f'{S1_URL}/web/api/v2.1/users/api-token-details',
            headers={'Authorization': f'ApiToken:{S1_TOKEN}'},
            json={ "data": { "apiToken": S1_TOKEN } },
            proxies=PROXY)
    except Exception as e:
        if DEBUG:
            print(f"[ ERROR ] SentinelOne connector: Failed to retrieve token expiration date: {e}")
        add_error_notification(f"SentinelOne connector: Failed to retrieve token expiration date: {e}")
        return None
    
    if r.status_code == 200 and 'data' in r.json():
        expires_at = r.json()['data']['expiresAt']
        dt = datetime.strptime(expires_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (dt - now).days + 1
    else:
        if DEBUG:
            print(f"[ ERROR ] Failed to retrieve token expiration date: {r.text}")
        add_error_notification(f"SentinelOne connector: Failed to retrieve token expiration date: {r.text}")
        return None


def get_redirect_threats_link(endpoint, date):
    """
    Generate a link to the SentinelOne threats page for a specific endpoint and date.
    :param endpoint: The endpoint name.
    :param date: Threat detection date, in 'YYYY-MM-DD' format.
    :return: A formatted URL string for the SentinelOne threats page.
    """
    init_globals()

    # convert date to datetime object
    start_date = datetime.combine(datetime.strptime(date, '%Y-%m-%d'), datetime.min.time())
    end_date = start_date + timedelta(days=1)

    # We add 000 because timerange is expected in epoch time milliseconds
    timerange = "{}000-{}000".format(
        int(start_date.timestamp()),
        int(end_date.timestamp())
        )
 
    return S1_THREATS_URL.format(endpoint, timerange)

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
