"""
Active Directory connector
"""

from connectors.utils import get_connector_conf
import logging
from ldap3 import Server, Connection, ALL

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Set to True for debugging purposes
DEBUG = False

# Retrieve connector settings from the database
LDAP_SERVER = get_connector_conf('activedirectory', 'LDAP_SERVER')
LDAP_PORT = int(get_connector_conf('activedirectory', 'LDAP_PORT'))
LDAP_SSL = get_connector_conf('activedirectory', 'LDAP_SSL')
LDAP_USER = get_connector_conf('activedirectory', 'LDAP_USER')
LDAP_PWD = get_connector_conf('activedirectory', 'LDAP_PWD')
LDAP_SEARCH_BASE = get_connector_conf('activedirectory', 'LDAP_SEARCH_BASE')
LDAP_ATTRIBUTES = {
	'USER_NAME': get_connector_conf('activedirectory', 'LDAP_ATTRIBUTES_USER_NAME'),
	'JOB_TITLE': get_connector_conf('activedirectory', 'LDAP_ATTRIBUTES_JOB_TITLE'),
	'BUSINESS_UNIT': get_connector_conf('activedirectory', 'LDAP_ATTRIBUTES_BUSINESS_UNIT'),
	'OFFICE': get_connector_conf('activedirectory', 'LDAP_ATTRIBUTES_OFFICE'),
	'COUNTRY': get_connector_conf('activedirectory', 'LDAP_ATTRIBUTES_COUNTRY')
}

def ldap_search(username):
    """
    Perform an LDAP search for a user by their username.
    
    :param username: The username to search for in the LDAP directory.
    :return: An LDAP entry if found, otherwise None.
    """

    server = Server(LDAP_SERVER, port=LDAP_PORT, use_ssl=LDAP_SSL, get_info=ALL)
    conn = Connection(server, LDAP_USER, LDAP_PWD, auto_bind=True)
    conn.search(
        LDAP_SEARCH_BASE,
        '(sAMAccountName={})'.format(username),
        attributes=[
            LDAP_ATTRIBUTES['USER_NAME'],
            LDAP_ATTRIBUTES['JOB_TITLE'],
            LDAP_ATTRIBUTES['BUSINESS_UNIT'],
            LDAP_ATTRIBUTES['OFFICE'],
            LDAP_ATTRIBUTES['COUNTRY']
            ]
        )
    if conn.entries:
        return conn.entries[0]
    else:
        logger.warning(f"No LDAP entry found for user {username}")
        return None
