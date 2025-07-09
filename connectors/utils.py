"""
Utils is used as a module for common functions used by connectors.
"""

from connectors.models import Connector, ConnectorConf
import re
import gzip
import base64
import urllib.parse
from io import BytesIO
from django.conf import settings
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)

DISABLE_RUN_DAILY_ON_ERROR = settings.DISABLE_RUN_DAILY_ON_ERROR


def get_connector_conf(connector_name, conf_name):
    """
    Get the value of a specific configuration for a given connector.
    
    :param connector_name: Name of the connector.
    :param conf_name: Name of the configuration key.
    :return: Value of the configuration or None if not found.
    """
    try:
        conf = ConnectorConf.objects.get(connector__name=connector_name, key=conf_name)
        return conf.value
    
    except ConnectorConf.DoesNotExist:
        return None

def is_connector_enabled(connector_name):
    """
    Check if a connector is enabled.
    
    :param connector_name: Name of the connector.
    :return: True if the connector is enabled, False otherwise.
    """
    try:
        connector = Connector.objects.get(name=connector_name)
        return connector.enabled
    except Connector.DoesNotExist:
        return False


def is_valid_md5(hash: str) -> bool:
    pattern = r'^[a-z-A-Z0-9]{32}$'
    return re.match(pattern, hash) is not None
    
def is_valid_sha1(hash: str) -> bool:
    pattern = r'^[a-z-A-Z0-9]{40}$'
    return re.match(pattern, hash) is not None
    
def is_valid_sha256(hash: str) -> bool:
    pattern = r'^[a-z-A-Z0-9]{64}$'
    return re.match(pattern, hash) is not None

def is_valid_ip(ip: str) -> bool:
    pattern = r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'
    return re.match(pattern, ip) is not None


def gzip_base64_urlencode(input_string):
    # Step 1: Gzip compress the string
    # Create a BytesIO buffer to hold the compressed data
    buffer = BytesIO()
    
    with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
        f.write(input_string.encode('utf-8'))
    
    # Get the compressed byte data
    compressed_data = buffer.getvalue()
    
    # Step 2: Base64 encode the compressed data
    base64_encoded = base64.b64encode(compressed_data).decode('utf-8')
    
    # Step 3: URL encode the Base64 string
    url_encoded = urllib.parse.quote(base64_encoded, safe='')  # encode all special chars
    
    return url_encoded

def manage_query_error(query, error_message):
    """
    Manage query errors by logging the error, updating the query status and saving the error message.
    :param query: Query object that failed.
    :param error_message: Error message to log and save.
    """

    logger.error(f"[ ERROR ] Query {query.name} failed. Check report for more info.")
    
    # if error, we set the query_error flag and save the error message
    query.query_error = True
    if len(error_message) > 500:
        error_message = "{} [...] {}".format(error_message[:250], error_message[-250:])

    query.query_error_message = error_message
    # if "error" message, and configured to auto-disable query,
    # remove query from future campaigns (until query is updated)
    if "error" in error_message.lower() and DISABLE_RUN_DAILY_ON_ERROR:
        query.run_daily = False
    # we save query
    query.save()
