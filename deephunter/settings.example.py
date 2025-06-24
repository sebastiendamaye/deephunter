from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '*****************************************************************'

DEBUG = False

# Update settings
UPDATE_ON = "release" # Possible values: commit|release
TEMP_FOLDER = "/data/tmp"
VENV_PATH = "/data/venv"

SHOW_LOGIN_FORM = False

ALLOWED_HOSTS = ['deephunter.domain.com']

# PingID / MS Entra ID
AUTHLIB_OAUTH_CLIENTS = {
    'pingid': {
        'client_id': 'YOUR_PINGID_CLIENT_ID',
        'client_secret': 'YOUR_PINGID_CLIENT_SECRET',
        'server_metadata_url': 'https://ping-sso.domain.com/.well-known/openid-configuration',
        'client_kwargs': {'scope': 'openid groups profile email'},
    },
    'entra_id': {
        'client_id': 'YOUR_ENTRA_ID_APP_ID',
        'client_secret': 'YOUR_ENTRA_ID_CLIENT_SECRET',
        'server_metadata_url': 'https://login.microsoftonline.com/<TENANT_ID>/.well-known/openid-configuration',
        'client_kwargs': {'scope': 'openid profile email'}
    }
}

# Which auth provider are you using (pingid|entra_id).
# Set to an empty string for local authentication
AUTH_PROVIDER = 'entra_id'

# Mapping of expected fields (left) vs token fields (right)
# You can use the debug return function of ./deephunter/views.py on line 64
# to check the token values
AUTH_TOKEN_MAPPING = {
    'username': 'unique_name',
    'first_name': 'given_name',
    'last_name': 'family_name',
    'email': 'upn',
    'groups': 'roles'
}

# To be granted access, users must be in one of these groups (viewer or manager)
# Mapping between DeepHunter groups (viewer, manager) and your AD groups, or Entra ID roles
USER_GROUPS_MEMBERSHIP = {
    'viewer': 'deephunterdev_usr',
    'manager': 'deephunterdev_pr'
}

# USER and GROUP. Used by deployment script to apply correct permissions
USER_GROUP = "user:group"

# GitHub URL used by the deploy.sh script to clone the repo
GITHUB_URL = "https://github.com/sebastiendamaye/deephunter.git"

# LDAP3 settings (used by timeline view to get additional info on user)
# Set LDAP_SERVER as an empty string to disable AD connection
LDAP_SERVER = 'gc.domain.com'
LDAP_PORT = 636
LDAP_SSL = True
LDAP_USER = 'SRVXXXXX@gad.domain.com'
LDAP_PWD = '***************************'
LDAP_SEARCH_BASE = 'DC=gad,DC=domain,DC=com'
LDAP_ATTRIBUTES = {
	'USER_NAME': 'displayName',
	'JOB_TITLE': 'title',
	'BUSINESS_UNIT': 'division',
	'OFFICE': 'physicalDeliveryOfficeName',
	'COUNTRY': 'co'
}

# Custom fields for threat hunting analytics
CUSTOM_FIELDS = {
    "c1": {
        "name": "VIP",
        "description": "VIP",
        "filter": "site.name contains:anycase ('VIP', 'Exec')"
        },
    "c2": {
        "name": "GSC",
        "description": "GSC",
        "filter": "site.name contains:anycase 'GSC'"
        },
    "c3": {}
    }

# Max retention. By default 90 days (3 months)
DB_DATA_RETENTION = 90

# Threshold for max number of hosts saved to DB for a given analytic (campaigns)
# By default 1000
CAMPAIGN_MAX_HOSTS_THRESHOLD = 1000
# Actions applied to analytics if CAMPAIGN_MAX_HOSTS_THRESHOLD is reached several times
ON_MAXHOSTS_REACHED = {
    "THRESHOLD": 3,
    "DISABLE_RUN_DAILY": True,
    "DELETE_STATS": False
}
# Automatically remove analytic from future campaigns if it failed
DISABLE_RUN_DAILY_ON_ERROR = True

# VirusTotal API key
VT_API_KEY = '*******************************************'

# MalwareBazaar API key
MALWAREBAZAAR_API_KEY = '*******************************************'

DBBACKUP_STORAGE_OPTIONS = {'location': '/data/backups/'}

# Keep ModelBackend around for per-user permissions and local superuser (admin)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

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
]

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

ROOT_URLCONF = 'deephunter.urls'

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

WSGI_APPLICATION = 'deephunter.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'deephunter',
        'USER': 'deephunter',
        'PASSWORD': '**********************',
        'HOST': '127.0.0.1',
        'PORT': '3306'
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Paris'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = '{}/static'.format(BASE_DIR)

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# SentinelOne API
S1_URL = 'https://my_tenant.sentinelone.net'
S1_TOKEN_EXPIRATION = 30
S1_TOKEN = '***************************************************'

PROXY = {
    'http': 'http://proxy:port',
    'https': 'http://proxy:port'
    }

### Legacy frontend
XDR_URL = 'https://xdr.eu1.sentinelone.net'
XDR_PARAMS = 'view=edr'
### New frontend
#XDR_URL = S1_URL
#XDR_PARAMS = '_categoryId=eventSearch'

### Legacy URL for threats
#S1_THREATS_URL = #'https://tenant.sentinelone.net/incidents/threats?filter={"computerName__contains":"{}","timeTitle":"Last%203%20Months"}'
### New URL for threats
S1_THREATS_URL = 'https://tenant.sentinelone.net/incidents/unified-alerts?_categoryId=threatsAndAlerts&_scopeLevel=global&alertsTable.filters=assetName__FULLTEXT%3D{}&alertsTable.timeRange=LAST_3_MONTHS'

LOGIN_URL = '/admin/login/'

### dbbackup settings (encrypted backups)
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_GPG_RECIPIENT = 'email@domain.com'

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

# Logout automatically after 1 hour
AUTO_LOGOUT = {
    'IDLE_TIME': timedelta(minutes=60),
    'REDIRECT_TO_LOGIN_IMMEDIATELY': True,
}

CELERY_BROKER_URL = "redis://localhost:6379"
CELERY_RESULT_BACKEND = "redis://localhost:6379"

# STAR rules
SYNC_STAR_RULES = True # True|False
STAR_RULES_PREFIX = '' # example: "TH_"
STAR_RULES_DEFAULTS = {
    'severity': 'High', # Low|Medium|High|Critical
    'status': 'Active', # Active|Draft
    'expiration': '10', # String. Expiration in days. Only if expirationMode set to 'Temporary'. Empty string to ignore
    'coolOffPeriod': '5', # String. Cool Off Period (in minutes). Empty string to ignore
    'treatAsThreat': 'Malicious', # Undefined(or empty)|Suspicious|Malicious.
    'networkQuarantine': 'true' # true|false
}

# Max number of distinct hostnames to consider an analytic as rare
RARE_OCCURRENCES_THRESHOLD = 10
