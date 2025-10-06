"""
Active Directory connector

Requirements
------------
pip install ldap3
"""

from connectors.utils import get_connector_conf
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPBindError, LDAPException
from notifications.utils import add_error_notification

_globals_initialized = False
def init_globals():
    global DEBUG, LDAP_SERVER, LDAP_PORT, LDAP_SSL, LDAP_USER, LDAP_PWD, LDAP_SEARCH_BASE, LDAP_ATTRIBUTES
    global _globals_initialized
    if not _globals_initialized:
        # Retrieve connector settings from the database
        DEBUG = False
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
        _globals_initialized = True

def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['ldap3']

def ldap_search(username):
    """
    Perform an LDAP search for a user by their username.
    
    :param username: The username to search for in the LDAP directory.
    :return: An LDAP entry if found, otherwise None.
    """
    init_globals()
    try:
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
            results = conn.entries[0]
        else:
            # add_error_notification(f"Active Directory connector: No LDAP entry found for user {username}")
            results = None
        
        # close connection
        conn.unbind()
        
        return results
    
    except LDAPBindError as e:
        add_error_notification(f"Active Directory connector: Failed to bind to LDAP server: Invalid credentials or DN: {e}")
        return None

    except LDAPException as e:
        add_error_notification(f"Active Directory connector: An LDAP error occurred: {e}")
        return None

    except Exception as e:
        add_error_notification(f"Active Directory connector: A general error occurred: {e}")
        return None
