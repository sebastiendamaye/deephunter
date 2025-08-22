"""
WHOIS connector
"""

from connectors.utils import get_connector_conf, is_valid_ip
import requests
from django.conf import settings
from bs4 import BeautifulSoup


_globals_initialized = False
def init_globals():
    global DEBUG, PROXY
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        _globals_initialized = True

def whois(ip):
    """
    Fetches WHOIS data for a given IP address.
    
    :param ip: The IP address to look up.
    :return: WHOIS data as a string or an error message
    """
    init_globals()
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
