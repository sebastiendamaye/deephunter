"""
VirusTotal connector
"""

from connectors.utils import get_connector_conf, is_valid_md5, is_valid_sha1, is_valid_sha256, is_valid_ip
import logging
import requests
from django.conf import settings
import vt

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Set to True for debugging purposes
DEBUG = False

# Import settings from Django settings
PROXY = settings.PROXY

# Retrieve connector settings from the database
API_KEY = get_connector_conf('virustotal', 'API_KEY')

def check_hash(hash):
    """
    Check if a hash exists in VirusTotal.
    
    :param hash: The hash to check.
    :return: Array with hash results if the hash exists, None otherwise.
    """
    if is_valid_md5(hash) or is_valid_sha1(hash) or is_valid_sha256(hash):        

        client = vt.Client(
            API_KEY,
            proxy=PROXY['https']
        )

        try:
            file = client.get_object("/files/{}".format(hash))
            return file
        
        except Exception as e:
            logger.error(f"Error checking hash {hash}: {e}")
            if DEBUG:
                raise e
            return None

def check_ip(ip):
    """
    Check if an IP address exists in VirusTotal.
    
    :param ip: The IP address to check.
    :return: Array with IP results if the IP exists, None otherwise.
    """
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
            logger.error(f"Error checking IP {ip}: {e}")
            if DEBUG:
                raise e
            return None
    else:
        logger.error(f"invalid IP {ip}")
        return None
    