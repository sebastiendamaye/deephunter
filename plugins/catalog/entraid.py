"""
EntraID plugin for DeepHunter

Requirements
------------
pip install Authlib

Description
-----------
This plugin integrates EntraID.
"""

from authlib.integrations.django_client import OAuth
from django.conf import settings
from connectors.utils import get_connector_conf
import ast

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY, CLIENT_ID, CLIENT_SECRET, SERVER_METADATA_URL, SCOPE, AUTH_TOKEN_MAPPING
    global AUTHLIB_OAUTH_CLIENTS, oauth, AUTH_TOKEN_MAPPING_USERNAME, AUTH_TOKEN_MAPPING_FIRST_NAME
    global AUTH_TOKEN_MAPPING_LAST_NAME, AUTH_TOKEN_MAPPING_EMAIL, AUTH_TOKEN_MAPPING_GROUPS, USER_GROUPS_MEMBERSHIP
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        CLIENT_ID = get_connector_conf('entraid', 'CLIENT_ID')
        CLIENT_SECRET = get_connector_conf('entraid', 'CLIENT_SECRET')
        SERVER_METADATA_URL = get_connector_conf('entraid', 'SERVER_METADATA_URL')
        SCOPE = get_connector_conf('entraid', 'SCOPE')
        AUTH_TOKEN_MAPPING_USERNAME = get_connector_conf('entraid', 'AUTH_TOKEN_MAPPING_USERNAME')
        AUTH_TOKEN_MAPPING_FIRST_NAME = get_connector_conf('entraid', 'AUTH_TOKEN_MAPPING_FIRST_NAME')
        AUTH_TOKEN_MAPPING_LAST_NAME = get_connector_conf('entraid', 'AUTH_TOKEN_MAPPING_LAST_NAME')
        AUTH_TOKEN_MAPPING_EMAIL = get_connector_conf('entraid', 'AUTH_TOKEN_MAPPING_EMAIL')
        AUTH_TOKEN_MAPPING_GROUPS = get_connector_conf('entraid', 'AUTH_TOKEN_MAPPING_GROUPS')
        USER_GROUPS_MEMBERSHIP = get_connector_conf('entraid', 'USER_GROUPS_MEMBERSHIP')
        oauth = OAuth()
        oauth.register(
            name='entra_id',
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            server_metadata_url=SERVER_METADATA_URL,
            client_kwargs={'scope': SCOPE}
        )
        _globals_initialized = True

def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['authlib']

def sso(request, redirect_uri):
    init_globals()
    return oauth.entra_id.authorize_redirect(request, redirect_uri)

def get_token(request):
    init_globals()
    token = oauth.entra_id.authorize_access_token(request)
    return token

def get_token_mapping():
    init_globals()
    return {
        'username': AUTH_TOKEN_MAPPING_USERNAME,
        'first_name': AUTH_TOKEN_MAPPING_FIRST_NAME,
        'last_name': AUTH_TOKEN_MAPPING_LAST_NAME,
        'email': AUTH_TOKEN_MAPPING_EMAIL,
        'groups': AUTH_TOKEN_MAPPING_GROUPS
    }

def get_user_groups_membership():
    init_globals()
    # Convert the string containing a dictionary into an actual Python dictionary object
    # Input must use single quotes
    return ast.literal_eval(USER_GROUPS_MEMBERSHIP)
