Settings
########

This is the settings page. Only relevant settings for DeepHunter are reported. For details about Django settings, please refer to the official Django documentation.

DEBUG
*****
- **Type**: Boolean
- **Possible values**: ``True`` or ``False``
- **Description**: Used to display debug information. Can be set to ``True`` in development environement, but always to ``False`` in a production environment.
- **Example**: ``DEBUG = True``

UPDATE_ON
*********

- **Type**: String
- **Description**: Choose how you should be notified about updates and what repository should be considered for updates. If you select ``commit``, you will be notified each time there is a new commit, and the upgrade script will download the very latest version of DeepHunter. If you select ``release``, you will only be notified about updates when a new version is released, and the upgrade script will download the latest release, instead of the latest commited code.
- **Possible values**: ``commit`` or ``release``
- **Example**:

.. code-block:: python

	UPDATE_ON = "release"

TEMP_FOLDER
***********

- **Type**: String
- **Description**: Used by the upgrade script. This is a temporary location where the current version of deephunter will be saved before upgrading. This can be used for easy rollback in case of error during the update process.
- **Example**:

.. code-block:: python

	TEMP_FOLDER = "/data/tmp"

VENV_PATH
*********

- **Type**: String
- **Description**: Used by the update script. This is your python virtual path.
- **Example**:

.. code-block:: python

	VENV_PATH = "/data/venv"

SHOW_LOGIN_FORM
***************
- **Type**: Boolean
- **Possible values**: ``True`` or ``False``
- **Description**: If set to ``True``, a login form with username/password fields will be shown to authenticate. If authentication is exclusively based on AD or PingID, it can be set to ``False``.
- **Example**: ``SHOW_LOGIN_FORM = True``

AUTHLIB_OAUTH_CLIENTS
*********************
- **Type**: Dictionary
- **Description**: Used to provide the PingID or Entra ID settings, for the authentication based on PingID or Entra ID. ``client_kwargs`` is used to specify information about the user, in case of successful authentication, in order to populate the local database.
- **Example**:

.. code-block:: python

	AUTHLIB_OAUTH_CLIENTS = {
		'pingid': {
			'client_id': 'deephunterdev',
			'client_secret': 'aB9cD3eF7gH1iJ2kL0mN4pQ6rS8tU5vWzYxZ3A7bC9dE2fG1hI0jsUQK3lM6nP9q',
			'server_metadata_url': 'https://ping-sso.domains.com/.well-known/openid-configuration',
			'client_kwargs': {'scope': 'openid groups profile email'},
		},
		'entra_id': {
			'client_id': 'deephunterdev',
			'client_secret': 'Ji0AA8tXKn6wnC9Vf7a211ykaMor5s',
			'server_metadata_url': 'https://login.microsoftonline.com/lmgh5678-12j4-97s2-n5b4-85f53h902k31/.well-known/openid-configuration',
			'client_kwargs': {'scope': 'openid profile email'}
		}
	}

AUTH_PROVIDER
*************
- **Type**: String
- **Description**: Authentication provider (in case you rely on an external authentication provider)
- **Possible values**: ``pingid`` or ``entra_id`` (if external authentication provider), or empty string (if local authentication).
- **Example**:

.. code-block:: python

	AUTH_PROVIDER = 'pingid'

AUTH_TOKEN_MAPPING
******************
- **Type**: Dictionary
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 64 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING = {
		'username': 'unique_name',
		'first_name': 'given_name',
		'last_name': 'family_name',
		'email': 'upn',
		'groups': 'roles'
	}

USER_GROUPS_MEMBERSHIP
**********************
- **Type**: Dictionary
- **Description**: If you are relying on an external authentication provider (i.e., PingID or Entra ID), you'll need to assign your users to AD groups or Entra ID roles. This variable is used to map DeepHunter's permissions (viewer and manager keys on the left side, respectively for read-only and write accesses) with your groups/roles (values on the right side). Only change the values (on the right side), not the keys (on the left side).

- **Example**: 

.. code-block:: python

	USER_GROUPS_MEMBERSHIP = {
		'viewer': 'deephunter_read',
		'manager': 'deephunter_write'
	}

USER_GROUP
**********
- **Type**: string (format should be ``user:group``)
- **Description**: User and group. Used by the deployment script (``qm/script/deploy.py``) to fix permissions.
- **Example**: 

.. code-block:: python
	
	USER_GROUP = "tomnook:users"

GITHUB_URL
**********
- **Type**: string
- **Description**: GitHub URL used by the ``deploy.sh`` script to clone the repo.
- **Example**: 

.. code-block:: python

	GITHUB_URL = "https://token@github.com/myuser/deephunter.git"

LDAP_SERVER
***********
- **Type**: string
- **Description**: LDAP server. Used to connect to the LDAP to gather additional information about a user based on a username (previously gathered by S1 using last logged in user), in the timeline view. To ignore the LDAP connection, set ``LDAP_SERVER`` to an empty string.
- **Example**:

.. code-block:: python

	# Set to empty string if you don't want to get additional user info from AD
	# LDAP_SERVER = ''
	LDAP_SERVER = 'gc.domain.com'
	
LDAP_PORT
*********
- **Type**: integer
- **Description**: LDAP port. Used to connect to the LDAP to gather additional information about a user based on a username (previously gathered by S1 using last logged in user), in the timeline view.
- **Example**:

.. code-block:: python
	
	LDAP_PORT = 636

LDAP_SSL
*********
- **Type**: boolean
- **Possible values**: ``True`` or ``False``
- **Description**: Force the LDAP connection to use SSL. Used to connect to the LDAP to gather additional information about a user based on a username (previously gathered by S1 using last logged in user), in the timeline view.
- **Example**:

.. code-block:: python
	
	LDAP_SSL = True

LDAP_USER
*********
- **Type**: string
- **Format**: ``user@domain``
- **Description**: LDAP user (e.g., a service account). Used to connect to the LDAP to gather additional information about a username (previously gathered by S1 using last logged in user), in the timeline view.
- **Example**:

.. code-block:: python

	LDAP_USER = 'SRV12345@gad.domain.com'

LDAP_PWD
********
- **Type**: string
- **Description**: LDAP password associated to ``LDAP_USER``. Used to connect to the LDAP to gather additional information about a user based on a machine name, in the timeline view.
- **Example**:

.. code-block:: python

	LDAP_PWD = 'Awes0m3#P455w9rD'

LDAP_SEARCH_BASE
****************
- **Type**: string
- **Description**: LDAP search base used to query the LDAP when searching for a user from a machine name. Usually composed of a serie of nested DC values.
- **Example**:

.. code-block:: python

	LDAP_SEARCH_BASE = 'DC=gad,DC=domain,DC=com'

LDAP_ATTRIBUTES
***************
- **Type**: string
- **Description**: LDAP attributes mapping. Expected values returned by the LDAP search should include the username, job title, business unit, office location, country. Depending on your LDAP architecture, fields could have different names. Use this mapping table to specify the corresponding fields.
- **Example**:

.. code-block:: python

	LDAP_ATTRIBUTES = {
		'USER_NAME': 'displayName',
		'JOB_TITLE': 'title',
		'BUSINESS_UNIT': 'division',
		'OFFICE': 'physicalDeliveryOfficeName',
		'COUNTRY': 'co'
	}

CUSTOM_FIELDS
*************
- **Type**: dictionary
- **Description**: The main dashboard of DeepHunter shows a table with statistics from the last campaign (number of matching events, number of machines, etc.). It is possible to add custom fields (additional columns), that are filtered values to make a break down of the number of matching hosts. For example, if you have defined a specific population for VP in your SentinelOne EDR, you may want to display the corresponding number in a dedicated column. There are up to 3 custom fields. For each, you define a ``name``, a ``description`` and the ``filter`` to apply to the query.
- **Example**:

.. code-block:: python

	CUSTOM_FIELDS = {
		"c1": {
			"name": "VIP",
			"description": "VP",
			"filter": "site.name contains:anycase ('VP', 'Exec')"
			},
		"c2": {
			"name": "GSC",
			"description": "GSC",
			"filter": "site.name contains:anycase 'GSC'"
			},
		"c3": {
			}
		}

DB_DATA_RETENTION
*****************
- **Type**: integer
- **Description**: number of days to keep the data in the local database. Default value: 90.
- **Example**:

.. code-block:: python

	DB_DATA_RETENTION = 90

CAMPAIGN_MAX_HOSTS_THRESHOLD
****************************
- **Type**: integer
- **Description**: Because hostname information is stored in the local database each day (campaigns), for each query, during a given number of days (retention), the database could quickly become too large if no threshold is defined. This threshold allows to define a maximum of hosts that would be stored for each query. Set to 1000 by default, as we may assume that a query that matches more than 1000 endpoints/day is not relevant enough for threat hunting.
- **Example**: 

.. code-block:: python

	CAMPAIGN_MAX_HOSTS_THRESHOLD = 1000

ON_MAXHOSTS_REACHED
*******************

- **Type**: dictionary, with following keys: ``THRESHOLD``: Integer, ``DISABLE_RUN_DAILY``: boolean, ``DELETE_STATS``: boolean.
- **Description**: If the threshold defined in ``CAMPAIGN_MAX_HOSTS_THRESHOLD`` is reached several times (defined by ``THRESHOLD``), it is possible to automatically remove the Threat Hunting Analytic from future campaigns (the ``run_daily`` flag will be set to ``False`` if ``DISABLE_RUN_DAILY`` is set), and/or delete the associated statistics (if ``DELETE_STATS`` is set).

.. note::

	The actions described above won't be applied to Threat Hunting analytics that have the flag ``run_daily_lock`` set. This is a way to protect some analytics from being automatically removed from the campaigns, or have the statistics deleted.

- **Example**: 

.. code-block:: python

	# Actions applied to analytics if CAMPAIGN_MAX_HOSTS_THRESHOLD is reached several times
	ON_MAXHOSTS_REACHED = {
		"THRESHOLD": 3,
		"DISABLE_RUN_DAILY": True,
		"DELETE_STATS": False
	}

DISABLE_RUN_DAILY_ON_ERROR
**************************

- **Type**: boolean.
- **Description**: Automatically remove analytic from future campaigns if it failed during a campaign or statistics regeneration process.
- **Example**: 

.. code-block:: python

	DISABLE_RUN_DAILY_ON_ERROR = True

VT_API_KEY
**********
- **Type**: string
- **Description**: VirusTotal API key used for the VirusTotal Hash Checker tool, available from the "Tools" menu. Also used by the "Netview" module to scan the reputation of the public IP addresses.
- **Example**: 

.. code-block:: python

	VT_API_KEY = 'r8h84wc9d2v6fj1n5ya7b0qf32kz3p62m14xd9s75boa01u75c6t8s5l3e9a0f7g'


MALWAREBAZAAR_API_KEY
*********************
- **Type**: string
- **Description**: Malware Bazaar API key used for the Malware Bazaar Hash Checker tool, available from the "Tools" menu.
- **Example**: 

.. code-block:: python

	MALWAREBAZAAR_API_KEY  = 'bffgwLSmWs9cmnkhqsGei0TMHw7RmjaW3nsBJZZWg03yEFsImA'

INSTALLED_APPS
**************
- **Type**: list
- **Description**: List of installed applications (initialized by django). Just make sure new DeepHunter modules are listed at the end (e.g., ``qm``, ``extensions``, ``reports``), and modules you are installing/using are also listed (e.g., ``dbbackup``).
- **Example**: 

.. code-block:: python

	# Application definition
	INSTALLED_APPS = [
		'django.contrib.admin',
		'django.contrib.auth',
		'django.contrib.contenttypes',
		'django.contrib.sessions',
		'django.contrib.messages',
		'django.contrib.staticfiles',
		'django_extensions',
		'dbbackup',
		'django_markup',
		'simple_history',
		'qm',
		'extensions',
		'reports',
	]

ROOT_URLCONF
************
- **Type**: string
- **Description**: Main URL file used by DeepHunter. Default value: ``deephunter.urls``. Do not modify this value.
- **Example**: 

.. code-block:: python
	
	ROOT_URLCONF = 'deephunter.urls'

DATABASES
*********
- **Type**: dictionary
- **Description**: Database settings. By default, configured to be used with MySQL/MariaDB. Refer to the Django documentation to use other backends.
- **Example**: 

.. code-block:: python

	DATABASES = {
		'default': {
			'ENGINE': 'django.db.backends.mysql',
			'NAME': 'deephunter',
			'USER': 'deephunter',
			'PASSWORD': 'D4t4b453_P455w0rD',
			'HOST': '127.0.0.1',
			'PORT': '3306'
		}
	}

TIME_ZONE
*********
- **Type**: string (``TIME_ZONE``), boolean (``USE_TZ``)
- **Description**: Timezone. Modify depending on where you are located.
- **Example**: 

.. code-block:: python

	TIME_ZONE = 'Europe/Paris'
	USE_TZ = True

STATIC_URL
**********
- **Type**: string
- **Description**: Related and absolute path for the static content (images, documentation, etc.).
- **Example**: 

.. code-block:: python

	STATIC_URL = 'static/'
	STATIC_ROOT = '/data/deephunter/static'


SentinelOne API
***************
- **Type**: string
- **Description**: ``S1_URL`` is the SentinelOne URL for your tenant and is used for any API call to SentinelOne. ``S1_TOKEN`` is the token associated to your API. Notice that tokens expire every month (``S1_TOKEN_EXPIRATION`` is set to 30 days by default) and the new token value should be updated (please use the ``update_s1_token.sh`` script to update your token, because it will take care of updating the renewal date).
- **Example**: 

.. code-block:: python

	S1_URL = 'https://yourtenant.sentinelone.net'
	S1_TOKEN_EXPIRATION = 30
	S1_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'

PROXY
*****
- **Type**: dictionary
- **Description**: Proxy settings for any Internet communication from DeepHunter, including API calls to S1.
- **Example**: 

.. code-block:: python

	PROXY = {
		'http': 'http://proxy:port',
		'https': 'http://proxy:port'
		}

SentinelOne frontend URL
************************
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
	S1_THREATS_URL = 'https://tenant.sentinelone.net/incidents/unified-alerts?_scopeLevel=global&_categoryId=threatsAndAlerts&uamAlertsTable.filters=assetName__FULLTEXT%3D{}&uamAlertsTable.timeRange=LAST_3_MONTHS'

LOGIN_URL
*********
- **Type**: string
- **Description**: URL to redirect to when logging out, or as first page when connecting. Shouldn't be changed.
- **Example**: 

.. code-block:: python

	LOGIN_URL = '/admin/login/'

DBBACKUP
********
- **Type**: dictionary (``DBBACKUP_STORAGE_OPTIONS``) and string (``DBBACKUP_STORAGE`` and ``DBBACKUP_GPG_RECIPIENT``)
- **Description**: ``DBBACKUP_STORAGE_OPTIONS`` is to specify the location of your backups. ``DBBACKUP_GPG_RECIPIENT`` should be the email address used by GPG for the encryption of the backups. Used by the ``./qm/scripts/backup.sh`` script.
- **Example**: 

.. code-block:: python

	### dbbackup settings (encrypted backups)
	DBBACKUP_STORAGE_OPTIONS = {'location': '/data/backups/'}
	DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
	DBBACKUP_GPG_RECIPIENT = 'email@domain.com'

LOGGING
*******
- **Type**: dictionary
- **Description**: Used to specify the file used for debugging information (``campaigns.log`` by default).
- **Example**: 

.. code-block:: python

	LOGGING = {
		# The version number of our log
		'version': 1,
		# django uses some of its own loggers for internal operations. In case you want to disable them just replace the False above with true.
		'disable_existing_loggers': False,
		# A handler for WARNING. It is basically writing the WARNING messages into a file called WARNING.log
		'handlers': {
			'file': {
				'level': 'ERROR',
				'class': 'logging.FileHandler',
				'filename': BASE_DIR / 'campaigns.log',
			},
			"console": {"class": "logging.StreamHandler"},
		},
		# A logger for WARNING which has a handler called 'file'. A logger can have multiple handler
		'loggers': {
		   # notice the blank '', Usually you would put built in loggers like django or root here based on your needs
			'': {
				'handlers': ['file'], #notice how file variable is called in handler which has been defined above
				'level': 'ERROR',
				'propagate': True,
			},
		},
	}

AUTO_LOGOUT
***********
- **Type**: dictionary
- **Description**: Used for session expiration (recommended). In case of inactivity, your session should auto-expire and you should be automatically disconnected after some time (defined in minutes with the ``IDLE_TIME`` parameter).
- **Example**: 

.. code-block:: python
	
	# Logout automatically after 1 hour
	AUTO_LOGOUT = {
		'IDLE_TIME': timedelta(minutes=60),
		'REDIRECT_TO_LOGIN_IMMEDIATELY': True,
	}

CELERY
******
- **Type**: string
- **Description**: Defines the address of the Celery broker.
- **Example**: 

.. code-block:: python

	CELERY_BROKER_URL = "redis://localhost:6379"
	CELERY_RESULT_BACKEND = "redis://localhost:6379"

STAR rules sync
***************

SYNC_STAR_RULES
===============

- **Type**: Boolean
- **Possible values**: ``True`` or ``False``
- **Description**: if ``SYNC_STAR_RULES`` is set to ``True``, STAR rules will be synchronized in SentinelOne when the STAR rule flag is set in DeepHunter queries and threat hunting analytics are created, updated or deleted. It can be set to ``False`` if you only want to use this flag in DeepHunter as information.
- **Example**: 

.. code-block:: python
	
	SYNC_STAR_RULES = True # True|False

STAR_RULES_PREFIX
=================

- **Type**: string
- **Description**: Prefix used to name STAR rules in SentinelOne. For example, if the prefix is ``TH_`` and you create a threat hunting analytic in DeepHunter named ``test_threat_hunting``, the STAR rule in SentinelOne will be named ``TH_test_threat_hunting``.
- **Example**: 

.. code-block:: python
	
	STAR_RULES_PREFIX = '' # example: "TH_"

STAR_RULES_DEFAULTS
===================

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

RARE_OCCURRENCES
================

- **Type**: integer
- **Description**: Used to define the threshold for rare occurrences. If a threat hunting analytic matches less than the defined number of distinct hosts (in the full retention), it is considered a rare occurrence.
- **Example**:
.. code-block:: python

	RARE_OCCURRENCES = 5
