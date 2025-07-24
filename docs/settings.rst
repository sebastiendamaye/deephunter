Settings
########

This is the settings page. Only relevant settings for DeepHunter are reported. For details about Django settings, please refer to the official Django documentation.

SECRET_KEY
**********
- **Type**: String
- **Description**: A secret key for a particular Django installation. This is used to provide cryptographic signing, and should be set to a unique, unpredictable value.

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

ALLOWED_HOSTS
*************
- **Type**: List of strings
- **Description**: A list of strings representing the host/domain names that this Django site can serve. This is a security measure to prevent HTTP Host header attacks, which are possible even under many seemingly-safe web server configurations.

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

GITHUB_LATEST_RELEASE_URL
*************************
- **Type**: string
- **Description**: GitHub URL to get the latest release.
- **Example**: 

.. code-block:: python

	GITHUB_LATEST_RELEASE_URL = 'https://api.github.com/repos/sebastiendamaye/deephunter/releases/latest'

GITHUB_COMMIT_URL
*****************
- **Type**: string
- **Description**: GitHub URL to get the latest commit ID.
- **Example**: 

.. code-block:: python

	GITHUB_COMMIT_URL = 'https://raw.githubusercontent.com/sebastiendamaye/deephunter/refs/heads/main/static/commit_id.txt'

DB_DATA_RETENTION
*****************
- **Type**: integer
- **Description**: number of days to keep the data in the local database. Default value: 90.
- **Example**:

.. code-block:: python

	DB_DATA_RETENTION = 90

RARE_OCCURRENCES_THRESHOLD
**************************
- **Type**: integer
- **Description**: Used to define the threshold for rare occurrences. If a threat hunting analytic matches less than the defined number of distinct hosts (in the full retention), it is considered a rare occurrence.
- **Example**:

.. code-block:: python

	RARE_OCCURRENCES_THRESHOLD = 5

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

ANALYTICS_PER_PAGE
******************

- **Type**: integer
- **Description**: Number of analytics displayed per page in the list view. This is used to paginate the list of analytics.
- **Example**:

.. code-block:: python
	
	ANALYTICS_PER_PAGE = 50

DAYS_BEFORE_REVIEW
******************

- **Type**: integer
- **Description**: Number of days before an analytic is considered for review.
- **Example**:

.. code-block:: python

	DAYS_BEFORE_REVIEW = 30

DISABLE_ANALYTIC_ON_REVIEW
**************************

- **Type**: boolean
- **Possible values**: ``True`` or ``False``
- **Description**: If set to ``True``, automatically disable analytics with status 'REVIEW'
- **Example**:

.. code-block:: python
	
	DISABLE_ANALYTIC_ON_REVIEW = False

AUTO_STATS_REGENERATION
***********************

- **Type**: boolean
- **Possible values**: ``True`` or ``False``
- **Description**: If set to ``True``, automatically regenerate stats when analytic query field is changed, or for new analytics
- **Example**:

.. code-block:: python

	AUTO_STATS_REGENERATION = True

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

AUTHENTICATION_BACKENDS
***********************
- **Type**: list
- **Description**: Keep ModelBackend around for per-user permissions and local superuser (admin).
- **Example**: 

.. code-block:: python

	AUTHENTICATION_BACKENDS = [
    	'django.contrib.auth.backends.ModelBackend',
	]

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
		'dbbackup', # django-dbbackup
		'django_markup',
		'simple_history',
		'qm',
		'extensions',
		'reports',
		'connectors',
	]

MIDDLEWARE
**********
- **Type**: list
- **Description**: List of middleware to use. Make sure to keep the default ones.
- **Example**:

.. code-block:: python

	MIDDLEWARE = [
		'django.middleware.security.SecurityMiddleware',
		'django.contrib.sessions.middleware.SessionMiddleware',
		'django.middleware.common.CommonMiddleware',
		'django.middleware.csrf.CsrfViewMiddleware',
		'django.contrib.auth.middleware.AuthenticationMiddleware',
		'django.contrib.messages.middleware.MessageMiddleware',
		'django.middleware.clickjacking.XFrameOptionsMiddleware',
		'simple_history.middleware.HistoryRequestMiddleware',
		'django_auto_logout.middleware.auto_logout',
	]

ROOT_URLCONF
************
- **Type**: string
- **Description**: Main URL file used by DeepHunter. Default value: ``deephunter.urls``. Do not modify this value.
- **Example**: 

.. code-block:: python
	
	ROOT_URLCONF = 'deephunter.urls'

TEMPLATES
*********
- **Type**: list
- **Description**: List of templates to use. Make sure to keep the default ones.
- **Example**:

.. code-block:: python
	
	TEMPLATES = [
		{
			'BACKEND': 'django.template.backends.django.DjangoTemplates',
			'DIRS': [],
			'APP_DIRS': True,
			'OPTIONS': {
				'context_processors': [
					'django.template.context_processors.debug',
					'django.template.context_processors.request',
					'django.contrib.auth.context_processors.auth',
					'django.contrib.messages.context_processors.messages',
					'django_auto_logout.context_processors.auto_logout_client',
				],
			},
		},
	]

WSGI_APPLICATION
****************
- **Type**: string
- **Description**: WSGI application used by Django. Default value: ``deephunter.wsgi.application``. Do not modify this value.
- **Example**:

.. code-block:: python

	WSGI_APPLICATION = 'deephunter.wsgi.application'

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

AUTH_PASSWORD_VALIDATORS
************************
- **Type**: list of dictionaries
- **Description**: Password validation settings. These validators are used to enforce password complexity and security. https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators
- **Example**:

.. code-block:: python

	AUTH_PASSWORD_VALIDATORS = [
		{
			'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
		},
		{
			'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
		},
		{
			'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
		},
		{
			'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
		},
	]

Internationalization settings
*****************************
- **Description**: https://docs.djangoproject.com/en/4.1/topics/i18n/
- **Example**:

.. code-block:: python

	LANGUAGE_CODE = 'en-us'
	TIME_ZONE = 'Europe/Paris'
	USE_I18N = True
	USE_TZ = True

STATIC_URL and STATIC_ROOT
**************************
- **Type**: string
- **Description**: Related and absolute path for the static content (images, documentation, etc.).
- **Example**: 

.. code-block:: python

	STATIC_URL = 'static/'
	STATIC_ROOT = '/data/deephunter/static'

DEFAULT_AUTO_FIELD
******************
- **Description**: Default primary key field type (https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field).
- **Example**:

.. code-block:: python

	DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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
