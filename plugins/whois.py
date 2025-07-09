"""
WHOIS connector
"""

from connectors.utils import get_connector_conf, is_valid_ip
import logging
import requests
from django.conf import settings
from bs4 import BeautifulSoup

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Set to True for debugging purposes
DEBUG = False

# Import settings from Django settings
PROXY = settings.PROXY

def whois(ip):
    """
    Fetches WHOIS data for a given IP address.
    
    :param ip: The IP address to look up.
    :return: WHOIS data as a string or an error message
    """
    if is_valid_ip(ip):
        response = requests.get(
            'https://www.whois.com/whois/{}/'.format(ip),
            proxies=PROXY
            )
        soup = BeautifulSoup(response.text, features="lxml")
        elements = soup.find_all('pre', attrs={'id': 'registryData'})
        if elements:
            return elements[0].text
        else:
            return 'No WHOIS data found for this IP address.'
    else:
        return 'Invalid IP format'
