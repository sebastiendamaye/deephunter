"""
FR #254 - Assign a type to connector settings for consistency and display
This script adds the necessary field types to the connector settings.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_254
"""

from connectors.models import ConnectorConf

def run():
    field_types = [
        {
            'connector': 'activedirectory',
            'key': 'LDAP_SERVER',
            'field_type': 'char',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_PORT',
            'field_type': 'int',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_SSL',
            'field_type': 'bool',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_USER',
            'field_type': 'char',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_PWD',
            'field_type': 'password',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_SEARCH_BASE',
            'field_type': 'char',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_ATTRIBUTES_USER_NAME',
            'field_type': 'char',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_ATTRIBUTES_JOB_TITLE',
            'field_type': 'char',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_ATTRIBUTES_BUSINESS_UNIT',
            'field_type': 'char',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_ATTRIBUTES_OFFICE',
            'field_type': 'char',
        },
        {
            'connector': 'activedirectory',
            'key': 'LDAP_ATTRIBUTES_COUNTRY',
            'field_type': 'char',
        },
        {
            'connector': 'sentinelone',
            'key': 'S1_URL',
            'field_type': 'url',
        },
        {
            'connector': 'sentinelone',
            'key': 'S1_TOKEN',
            'field_type': 'password',
        },
        {
            'connector': 'sentinelone',
            'key': 'XDR_URL',
            'field_type': 'url',
        },
        {
            'connector': 'sentinelone',
            'key': 'XDR_PARAMS',
            'field_type': 'char',
        },
        {
            'connector': 'sentinelone',
            'key': 'S1_THREATS_URL',
            'field_type': 'url',
        },
        {
            'connector': 'sentinelone',
            'key': 'SYNC_STAR_RULES',
            'field_type': 'bool',
        },
        {
            'connector': 'sentinelone',
            'key': 'STAR_RULES_PREFIX',
            'field_type': 'char',
        },
        {
            'connector': 'sentinelone',
            'key': 'STAR_RULES_DEFAULT_SEVERITY',
            'field_type': 'char',
        },
        {
            'connector': 'sentinelone',
            'key': 'STAR_RULES_DEFAULT_STATUS',
            'field_type': 'char',
        },
        {
            'connector': 'sentinelone',
            'key': 'STAR_RULES_DEFAULT_EXPIRATION',
            'field_type': 'int',
        },
        {
            'connector': 'sentinelone',
            'key': 'STAR_RULES_DEFAULT_COOLOFFPERIOD',
            'field_type': 'int',
        },
        {
            'connector': 'sentinelone',
            'key': 'STAR_RULES_DEFAULT_TREATASTHREAT',
            'field_type': 'bool',
        },
        {
            'connector': 'sentinelone',
            'key': 'STAR_RULES_DEFAULT_NETWORKQUARANTINE',
            'field_type': 'bool',
        },
        {
            'connector': 'virustotal',
            'key': 'API_KEY',
            'field_type': 'password',
        },
        {
            'connector': 'malwarebazaar',
            'key': 'API_KEY',
            'field_type': 'password',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'TENANT_ID',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'CLIENT_ID',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'CLIENT_SECRET',
            'field_type': 'password',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'WORKSPACE_ID',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'SYNC_RULES',
            'field_type': 'bool',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'SUBSCRIPTION_ID',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'RESOURCE_GROUP',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'WORKSPACE_NAME',
            'field_type': 'char',
        },
        {
            'connector': 'sentinelone',
            'key': 'QUERY_ERROR_INFO',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftsentinel',
            'key': 'QUERY_ERROR_INFO',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftdefender',
            'key': 'TENANT_ID',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftdefender',
            'key': 'CLIENT_ID',
            'field_type': 'char',
        },
        {
            'connector': 'microsoftdefender',
            'key': 'CLIENT_SECRET',
            'field_type': 'password',
        },
        {
            'connector': 'microsoftdefender',
            'key': 'SYNC_RULES',
            'field_type': 'bool',
        },
        {
            'connector': 'microsoftdefender',
            'key': 'QUERY_ERROR_INFO',
            'field_type': 'char',
        },
        {
            'connector': 'gemini',
            'key': 'API_KEY',
            'field_type': 'password',
        },
        {
            'connector': 'gemini',
            'key': 'MODEL',
            'field_type': 'char',
        },
        {
            'connector': 'gemini',
            'key': 'TEMPERATURE',
            'field_type': 'float',
        },
        {
            'connector': 'gemini',
            'key': 'TOP_P',
            'field_type': 'float',
        },
        {
            'connector': 'gemini',
            'key': 'TOP_K',
            'field_type': 'int',
        },
        {
            'connector': 'gemini',
            'key': 'MAX_OUTPUT_TOKENS',
            'field_type': 'int',
        }
    ]

    for field in field_types:
        try:
            conf = ConnectorConf.objects.get(connector__name=field['connector'], key=field['key'])
            conf.fieldtype = field['field_type']
            conf.save()
            print(f"Updated {field['connector']} - {field['key']} to type {field['field_type']}")
        except ConnectorConf.DoesNotExist:
            print(f"Configuration {field['connector']} - {field['key']} does not exist, skipping.")
