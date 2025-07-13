Plugins: SentinelOne
####################

Settings
********

SentinelOne API
===============
- **Type**: string
- **Description**: ``S1_URL`` is the SentinelOne URL for your tenant and is used for any API call to SentinelOne. ``S1_TOKEN`` is the token associated to your API. Notice that tokens expire every month (``S1_TOKEN_EXPIRATION`` is set to 30 days by default) and the new token value should be updated (please use the ``update_s1_token.sh`` script to update your token, because it will take care of updating the renewal date).
- **Example**: 

.. code-block:: python

	S1_URL = 'https://yourtenant.sentinelone.net'
	S1_TOKEN_EXPIRATION = 30
	S1_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'


SentinelOne frontend URL
========================
- **Type**: string
- **Description**: Address and parameters to use to point to SentinelOne frontend from the timeline view. Depending on the interface you have enabled (legacy frontend of new frontend), the URL and parameters are different. Make sure to uncomment the correct settings and comment out the ones to ignore. Notice that ``S1_THREATS_URL`` is dnyamically rendered by the Django view using ``format`` to evaluate the correct hostname. This is why the ``{}`` string appears in the URL.
- **Example**: 

.. code-block:: python
	
	### Legacy frontend
	XDR_URL = 'https://xdr.eu1.sentinelone.net'
	XDR_PARAMS = 'view=edr'
	### New frontend
	#XDR_URL = 'https://tenant.sentinelone.net'
	#XDR_PARAMS = '_categoryId=eventSearch'
	
	### Legacy URL for threats
	#S1_THREATS_URL = #'https://tenant.sentinelone.net/incidents/threats?filter={"computerName__contains":"{}","timeTitle":"Last%203%20Months"}'
	### New URL for threats
	S1_THREATS_URL = 'https://tenant.sentinelone.net/incidents/unified-alerts?_categoryId=threatsAndAlerts&_scopeLevel=global&alertsTable.filters=assetName__FULLTEXT%3D{}&alertsTable.timeRange=LAST_3_MONTHS'


STAR rules sync
===============

SYNC_STAR_RULES
---------------

- **Type**: Boolean
- **Possible values**: ``True`` or ``False``
- **Description**: if ``SYNC_STAR_RULES`` is set to ``True``, STAR rules will be synchronized in SentinelOne when the STAR rule flag is set in DeepHunter queries and threat hunting analytics are created, updated or deleted. It can be set to ``False`` if you only want to use this flag in DeepHunter as information.
- **Example**: 

.. code-block:: python
	
	SYNC_STAR_RULES = True # True|False

STAR_RULES_PREFIX
-----------------

- **Type**: string
- **Description**: Prefix used to name STAR rules in SentinelOne. For example, if the prefix is ``TH_`` and you create a threat hunting analytic in DeepHunter named ``test_threat_hunting``, the STAR rule in SentinelOne will be named ``TH_test_threat_hunting``.
- **Example**: 

.. code-block:: python
	
	STAR_RULES_PREFIX = '' # example: "TH_"

STAR_RULES_DEFAULTS
-------------------

- **Type**: dictionary of strings.
- **Description**: default values for the creation of STAR rules. Notice that modifications about severity, expiration, cool off settings and response actions you may have applied to STAR rules in SentinelOne are preserved when threat hunting analytics are updated.
- **Example**: 

.. code-block:: python
	
	STAR_RULES_DEFAULTS = {
		'severity': 'High', # Low|Medium|High|Critical
		'status': 'Active', # Active|Draft
		'expiration': '', # String. Expiration in days. Only if expirationMode set to 'Temporary'. Empty string to ignore
		'coolOffPeriod': '', # String. Cool Off Period (in minutes). Empty string to ignore
		'treatAsThreat': '', # Undefined(or empty)|Suspicious|Malicious.
		'networkQuarantine': 'false' # true|false
	}

