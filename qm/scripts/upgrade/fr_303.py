"""
FR #303 - Make EntraID and PingID connectors instead of hard-coded
This script adds the PingID and EntraID connectors and their default settings.
"""

from connectors.models import Connector, ConnectorConf

def run():

    connectors_to_add = [
        {
            'name': 'pingid',
            'description': """PingID is a multi-factor authentication (MFA) service from Ping Identity that adds an extra layer of security to user sign-ins. It is a cloud-based service that uses a mobile app and various methods like push notifications, one-time passcodes (OTPs) via SMS or email, and QR codes to verify user identities, making it more secure than just a password. This service is used for both workforce (employees, contractors) and customer identity management.""",
            'domain': 'authentication',
            'conf': [
                {
                    'key': 'CLIENT_ID',
                    'value': 'thisisclientid',
                    'fieldtype': 'char',
                    'description': 'The Client ID provided by PingID for OAuth2 authentication.',
                },
                {
                    'key': 'CLIENT_SECRET',
                    'value': '**************',
                    'fieldtype': 'password',
                    'description': 'The Client Secret provided by PingID for OAuth2 authentication.',
                },
                {
                    'key': 'SERVER_METADATA_URL',
                    'value': 'https://ping-sso.domains.com/.well-known/openid-configuration',
                    'fieldtype': 'char',
                    'description': 'The Server Metadata URL for PingID.',
                },
                {
                    'key': 'SCOPE',
                    'value': 'openid groups profile email',
                    'fieldtype': 'char',
                    'description': 'Additional parameters for the client.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_USERNAME',
                    'value': 'sub',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for username.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_FIRST_NAME',
                    'value': 'firstName',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for first name.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_LAST_NAME',
                    'value': 'lastName',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for last name.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_EMAIL',
                    'value': 'email',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for email.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_GROUPS',
                    'value': 'groups',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for groups.',
                },
                {
                    'key': 'USER_GROUPS_MEMBERSHIP',
                    'value': """{'viewer': 'AD_deephunter_usr', 'manager': 'AD_deephunter_pr', 'threathunter': 'AD_deephunter_th'}""",
                    'fieldtype': 'char',
                    'description': 'User groups membership mapping.',
                },
            ],
        },
        {
            'name': 'entraid',
            'description': """Entra ID is the new name for Microsoft's cloud-based identity and access management service, formerly known as Azure Active Directory. It helps organizations manage and secure user identities to control access to applications, data, and resources across multicloud and on-premises environments. Entra ID uses Zero Trust principles to ensure that only authenticated and authorized users can access what they need.""",
            'domain': 'authentication',
            'conf': [
                {
                    'key': 'CLIENT_ID',
                    'value': 'thisisclientid',
                    'fieldtype': 'char',
                    'description': 'The Client ID provided by Entra ID for OAuth2 authentication.',
                },
                {
                    'key': 'CLIENT_SECRET',
                    'value': '**************',
                    'fieldtype': 'password',
                    'description': 'The Client Secret provided by Entra ID for OAuth2 authentication.',
                },
                {
                    'key': 'SERVER_METADATA_URL',
                    'value': 'https://login.microsoftonline.com/foo-blah-replace-content/.well-known/openid-configuration',
                    'fieldtype': 'char',
                    'description': 'The Server Metadata URL for Entra ID.',
                },
                {
                    'key': 'SCOPE',
                    'value': 'openid profile email',
                    'fieldtype': 'char',
                    'description': 'Additional parameters for the client.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_USERNAME',
                    'value': 'unique_name',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for username.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_FIRST_NAME',
                    'value': 'given_name',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for first name.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_LAST_NAME',
                    'value': 'family_name',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for last name.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_EMAIL',
                    'value': 'upn',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for email.',
                },
                {
                    'key': 'AUTH_TOKEN_MAPPING_GROUPS',
                    'value': 'roles',
                    'fieldtype': 'char',
                    'description': 'Authentication token mapping for groups.',
                },
                {
                    'key': 'USER_GROUPS_MEMBERSHIP',
                    'value': """{'viewer': 'AD_deephunter_usr', 'manager': 'AD_deephunter_pr'}""",
                    'fieldtype': 'char',
                    'description': 'User groups membership mapping.',
                },
            ],
        },
    ]

    for connector_to_add in connectors_to_add:
        print("=================================")
        connector, created = Connector.objects.get_or_create(
            name=connector_to_add['name'],
            defaults={
                'description': connector_to_add['description'],
                'domain': connector_to_add['domain'],
            })
        if created:
            print(f"Added connector: {connector.name}")
        else:
            print(f"Connector already exists: {connector.name}")

        for connector_conf in connector_to_add['conf']:
            connectorconf, created = ConnectorConf.objects.get_or_create(
                connector=connector,
                key=connector_conf['key'],
                defaults={
                    'value': connector_conf['value'],
                    'fieldtype': connector_conf['fieldtype'],
                    'description': connector_conf['description'],
                })
            if created:
                print(f" - Added config: {connectorconf.key} = {connectorconf.value}")
            else:
                print(f" - Existing config: {connectorconf.key} = {connectorconf.value}")
