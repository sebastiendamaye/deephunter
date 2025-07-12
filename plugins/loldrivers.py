"""
LOLDrivers connector
"""

from connectors.utils import get_connector_conf
import logging
import requests
from django.conf import settings
from bs4 import BeautifulSoup

# Get an instance of a logger
logger = logging.getLogger(__name__)

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        _globals_initialized = True

def get_sha256_hashes():
    """
    Fetches SHA256 hashes of LOLDrivers from the website.
    :return: A list of SHA256 hashes found on the LOLDrivers website.
    """
    init_globals()
    lol_hashes = []
    response = requests.get(
        'https://www.loldrivers.io/',
        proxies=PROXY
        )
    soup = BeautifulSoup(response.text, "lxml")
    #Created a list of lol driver SHA256 hashes
    for link in soup.find_all("a", href=True):
        if len(link.text) == 64:
            lol_hashes.append(str(link.text))
    return lol_hashes
