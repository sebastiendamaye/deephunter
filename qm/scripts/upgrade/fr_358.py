"""
FR #358 - SentinelOne connector: PowerQueries now rely on the Long Running Query (LRQ) API
This script adds the SentinelOne connector (if missing) and its settings, including the new S1_ACCOUNT_IDS setting.
"""

from connectors.models import Connector, ConnectorConf

def run():

    connectors_to_add = [
        {
            'name': 'sentinelone',
            'description': """SentinelOne connector""",
            'domain': 'analytics',
            'conf': [
                {
                    'key': 'S1_URL',
                    'value': 'https://tenant.sentinelone.net',
                    'fieldtype': 'url',
                    'description': 'S1_URL is the SentinelOne URL for your tenant and is used for any API call to SentinelOne.',
                },
                {
                    'key': 'S1_TOKEN',
                    'value': '*****',
                    'fieldtype': 'password',
                    'description': 'S1_TOKEN is the token associated to your API.',
                },
                {
                    'key': 'XDR_URL',
                    'value': 'https://xdr.eu1.sentinelone.net',
                    'fieldtype': 'url',
                    'description': """URL address to use to point to SentinelOne frontend from the timeline view. For the legacy UI, you can use "https://xdr.eu1.sentinelone.net". For the new UI, use the same URL as for the "S1_URL" parameter.""",
                },
                {
                    'key': 'XDR_PARAMS',
                    'value': 'view=edr',
                    'fieldtype': 'char',
                    'description': """Parameters associated to the URL address used to point to SentinelOne frontend from the timeline view. For the legacy UI, you can use "view=edr" parameters. For the new UI, use "_categoryId=eventSearch".""",
                },
                {
                    'key': 'S1_THREATS_URL',
                    'value': 'https://tenant.sentinelone.net/incidents/unified-alerts?_categoryId=threatsAndAlerts&_scopeLevel=global&alertsTable.filters=assetName__FULLTEXT%3D{}&alertsTable.timeRange=LAST_3_MONTHS',
                    'fieldtype': 'url',
                    'description': """URL address used to point to the threats page in SentinelOne. Notice that S1_THREATS_URL is dnyamically rendered by the Django view using format to evaluate the correct hostname. This is why the {} string appears in the URL. For legacy UI, use the following URL:  'https://tenant.sentinelone.net/incidents/threats?filter={"computerName__contains":"{}","timeTitle":"Last%203%20Months"}'. For the new UI, use 'https://tenant.sentinelone.net/incidents/unified-alerts?_categoryId=threatsAndAlerts&_scopeLevel=global&alertsTable.filters=assetName__FULLTEXT%3D{}&alertsTable.timeRange=LAST_3_MONTHS'""",
                },
                {
                    'key': 'SYNC_STAR_RULES',
                    'value': 'True',
                    'fieldtype': 'bool',
                    'description': 'If set to True, DeepHunter will automatically synchronize your threat hunting analytics (create, modify or delete) with corresponding STAR rules in SentinelOne. Possible values: True|False',
                },
                {
                    'key': 'STAR_RULES_PREFIX',
                    'value': 'TH_',
                    'fieldtype': 'char',
                    'description': """STAR rules created from DeepHunter to SentinelOne can have a prefix in their name (e.g. "TH_") for an easier identification. Beware if you change this value while some STAR rules have already been synchronized, as you will need to manually change the name of existing rules in S1 to match the new prefix.""",
                },
                {
                    'key': 'STAR_RULES_DEFAULT_SEVERITY',
                    'value': 'High',
                    'fieldtype': 'char',
                    'description': 'The rule severity in your environment. Possible values: Low|Medium|High|Critical',
                },
                {
                    'key': 'STAR_RULES_DEFAULT_STATUS',
                    'value': 'Active',
                    'fieldtype': 'char',
                    'description': 'Defines the rule is Enabled (Activated and sends alerts if triggered) or Disabled. Possible values: Active|Draft',
                },
                {
                    'key': 'STAR_RULES_DEFAULT_EXPIRATION',
                    'value': '',
                    'fieldtype': 'int',
                    'description': """If the rule is Temporary, enter the expiration delay (in days) for the rule. If set, it will automatically consider expirationMode is "Temporary". Empty string to ignore""",
                },
                {
                    'key': 'STAR_RULES_DEFAULT_COOLOFFPERIOD',
                    'value': '',
                    'fieldtype': 'int',
                    'description': 'Receive only one alert and suppress additional alerts when a rule is triggered multiple times during the cool-off period. Mitigation actions set in the rule will not be applied to suppressed alerts. Leave empty to ignore.',
                },
                {
                    'key': 'STAR_RULES_DEFAULT_TREATASTHREAT',
                    'value': 'False',
                    'fieldtype': 'bool',
                    'description': 'Defines the Treat as a threat auto response. Possible values: Undefined(or empty)|Suspicious|Malicious',
                },
                {
                    'key': 'STAR_RULES_DEFAULT_NETWORKQUARANTINE',
                    'value': 'False',
                    'fieldtype': 'bool',
                    'description': 'Set to True to automatically quarantine the alerted endpoints. Possible values: true|false',
                },
                {
                    'key': 'QUERY_ERROR_INFO',
                    'value': r"""status['"]:\s?['"]FINISHED['"]""",
                    'fieldtype': 'char',
                    'description': 'Regular expression to filter what should be considered INFO instead of ERROR in query error message',
                },
                {
                    'key': 'S1_ACCOUNT_IDS',
                    'value': '',
                    'fieldtype': 'char',
                    'description': 'Comma-separated account IDs (optional) to query. If empty, it queries the whole tenant.',
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
