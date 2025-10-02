"""
VirusTotal connector
"""

from connectors.utils import get_connector_conf, is_valid_md5, is_valid_sha1, is_valid_sha256, is_valid_ip
import requests
from django.conf import settings
import vt
from notifications.utils import add_error_notification

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY, API_KEY
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        API_KEY = get_connector_conf('virustotal', 'API_KEY')
        _globals_initialized = True

def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['requests', 'vt']

def check_hash(hash):
    """
    Check if a hash exists in VirusTotal.
    
    :param hash: The hash to check.
    :return: Array with hash results if the hash exists, None otherwise.
    """
    init_globals()
    if is_valid_md5(hash) or is_valid_sha1(hash) or is_valid_sha256(hash):        

        client = vt.Client(
            API_KEY,
            proxy=PROXY['https']
        )

        try:
            file = client.get_object("/files/{}".format(hash))
            return file
        
        except Exception as e:
            add_error_notification(f"VirusTotal connector: Error checking hash {hash}: {e}")
            if DEBUG:
                raise e
            return None

def check_ip(ip):
    """
    Check if an IP address exists in VirusTotal.
    
    :param ip: The IP address to check.
    :return: Array with IP results if the IP exists, None otherwise.
    """
    init_globals()
    if is_valid_ip(ip):

        headers = {
            'x-apikey': API_KEY,
            'accept': 'application/json'
        }

        try:
            response = requests.get(
                f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
                headers=headers,
                proxies=PROXY
                )
            return response.json()['data']
        
        except Exception as e:
            add_error_notification(f"VirusTotal connector: Error checking IP {ip}: {e}")
            if DEBUG:
                raise e
            return None
    else:
        add_error_notification(f"VirusTotal connector: invalid IP {ip}")
        return None
    