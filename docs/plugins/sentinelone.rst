SentinelOne
###########

Description
***********

Connector to connect to SentinelOne EDR (https://www.sentinelone.com/). This plugin currently features:

- Query: Perform a PowerQuery to SentinelOne and get statistics in DeepHunter.
- Sync STAR rules (create, update and delete STAR rules in SentinelOne when threat hunting analytics are created, updated or deleted in DeepHunter)
- get threats from SentinelOne and display them in the timeline view
- get machine details from SentinelOne and display them in the machine details view
- get user owner from a machine name
- get applications
- get network connections
- get token expiration date

Star rules synchronization
**************************
DeepHunter synchronizes the query of threat hunting analytics with STAR rules in SentinelOne, when the STAR rule flag is set.

STAR rules are created with the following default properties:

.. list-table::
   :widths: 25 50 50
   :header-rows: 1

   * - 
     - Creation
     - Update
   * - Scope
     - Global
     - Global
   * - PowerQuery version
     - 2.0
     - 2.0
   * - Severity
     - Defined in the settings
     - (existing value preserved)
   * - Description
     - "Rule sync from DeeHunter"
     - (existing value preserved)
   * - Rule Type
     - Single Event
     - Single Event
   * - Status
     - Active
     - Active
   * - expirationMode
     - Defined in the settings
     - (existing value preserved)
   * - coolOffSettings
     - Defined in the settings
     - (existing value preserved)
   * - treatAsThreat
     - Defined in the settings
     - (existing value preserved)
   * - networkQuarantine
     - Defined in the settings
     - (existing value preserved)

The following logic is applied:

- if a new threat hunting analytic is created with the STAR rule flag set in DeepHunter, a STAR rule will be created in SentinelOne
- if a threat hunting analytic with the STAR rule flag set is deleted in DeepHunter, the associated STAR rule will be deleted in SentinelOne
- if a threat hunting analytic is updated in DeepHunter, with the STAR rule flag newly set, a corresponding STAR rule will be created in SentinelOne
- if a threat hunting analytic is updated in DeepHunter, with the STAR rule flag removed (previously set), the associated STAR rule will be deleted in SentinelOne
- if a threat hunting analytic is updated in DeepHunter, with the STAR rule flag set (previously set), the associated STAR rule will be updated in SentinelOne (see above table for updated fields)

Settings
********

S1_URL
======
- **Type**: string
- **Description**: ``S1_URL`` is the SentinelOne URL for your tenant and is used for any API call to SentinelOne.
- **Example**: 

.. code-block:: python

	S1_URL = 'https://yourtenant.sentinelone.net'

S1_TOKEN
========
- **Type**: string
- **Description**: Token used to authenticate against SentinelOne API. You can generate a token in the SentinelOne console. The token is valid for 30 days.
- **Example**: 

.. code-block:: python

	S1_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30'

XDR_URL and XDR_PARAMS
======================

- **Type**: string
- **Description**: Address and parameters to use to point to SentinelOne frontend from the timeline view. Depending on the interface you have enabled (legacy frontend of new frontend), the URL and parameters are different.
- **Example**: 

.. code-block:: python

	# Legacy frontend
	XDR_URL = 'https://xdr.eu1.sentinelone.net'
	XDR_PARAMS = 'view=edr'
	# New frontend
	#XDR_URL = 'https://tenant.sentinelone.net'
	#XDR_PARAMS = '_categoryId=eventSearch'


S1_THREATS_URL
==============
- **Type**: string
- **Description**: Notice that ``S1_THREATS_URL`` is dnyamically rendered by the Django view using ``format`` to evaluate the correct hostname. This is why the ``{}`` string appears in the URL.
- **Example**: 

.. code-block:: python
		
	### Legacy URL for threats
	#S1_THREATS_URL = #'https://tenant.sentinelone.net/incidents/threats?filter={"computerName__contains":"{}","timeTitle":"Last%203%20Months"}'
	### New URL for threats
	S1_THREATS_URL = 'https://tenant.sentinelone.net/incidents/unified-alerts?_categoryId=threatsAndAlerts&_scopeLevel=global&alertsTable.filters=assetName__FULLTEXT%3D{}&alertsTable.timeRange=LAST_3_MONTHS'

SYNC_STAR_RULES
===============
- **Type**: Boolean
- **Possible values**: ``True`` or ``False``
- **Description**: if ``SYNC_STAR_RULES`` is set to ``True``, STAR rules will be synchronized in SentinelOne when the STAR rule flag is set in DeepHunter queries and threat hunting analytics are created, updated or deleted. It can be set to ``False`` if you only want to use this flag in DeepHunter as information.
- **Example**: 

.. code-block:: python
	
	SYNC_STAR_RULES = True

STAR_RULES_PREFIX
=================

- **Type**: string
- **Description**: Prefix used to name STAR rules in SentinelOne. For example, if the prefix is ``TH_`` and you create a threat hunting analytic in DeepHunter named ``test_threat_hunting``, the STAR rule in SentinelOne will be named ``TH_test_threat_hunting``.
- **Example**: 

.. code-block:: python
	
	STAR_RULES_PREFIX = '' # example: "TH_"

STAR_RULES_DEFAULT_SEVERITY
===========================
- **Type**: string
- **Description**: The rule severity in your environment.
- **Possible values**: Low|Medium|High|Critical
- **Example**: 

.. code-block:: python
	
	STAR_RULES_DEFAULT_SEVERITY = 'High'

STAR_RULES_DEFAULT_STATUS
=========================
- **Type**: string
- **Description**: Defines the rule is Enabled (Activated and sends alerts if triggered) or Disabled.
- **Possible values**: Active|Draft
- **Example**: 

.. code-block:: python
	
	STAR_RULES_DEFAULT_STATUS = 'Active'

STAR_RULES_DEFAULT_EXPIRATION
=============================
- **Type**: string
- **Description**: If the rule is Temporary, enter the expiration delay (in days) for the rule. If set, it will automatically consider expirationMode is "Temporary". Empty string to ignore
- **Example**: 

.. code-block:: python
	
	STAR_RULES_DEFAULT_EXPIRATION = ''

STAR_RULES_DEFAULT_COOLOFPERIOD
===============================
- **Type**: integer (or empty string to ignore)
- **Description**: Receive only one alert and suppress additional alerts when a rule is triggered multiple times during the cool-off period. Mitigation actions set in the rule will not be applied to suppressed alerts. Leave empty to ignore.
- **Example**: 

.. code-block:: python
	
	STAR_RULES_DEFAULT_COOLOFPERIOD = ''

STAR_RULES_DEFAULT_TREATASTHREAT
================================
- **Type**: string
- **Description**: Defines the Treat as a threat auto response.
- **Possible values**: Undefined(or empty)|Suspicious|Malicious
- **Example**: 

.. code-block:: python
	
	STAR_RULES_DEFAULT_TREATASTHREAT = ''

STAR_RULES_DEFAULT_NETWORK_QUARANTINE
=====================================
- **Type**: boolean
- **Description**: Set to True to automatically quarantine the alerted endpoints.
- **Possible values**: true|false
- **Example**: 

.. code-block:: python
	
	STAR_RULES_DEFAULT_NETWORK_QUARANTINE = 'false'
