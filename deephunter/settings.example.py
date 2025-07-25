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

# Should the login form be displayed?
# It can be disabled if you are using an external authentication provider (PingID, EntraID)
SHOW_LOGIN_FORM = True

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
GITHUB_LATEST_RELEASE_URL = 'https://api.github.com/repos/sebastiendamaye/deephunter/releases/latest'
GITHUB_COMMIT_URL = 'https://raw.githubusercontent.com/sebastiendamaye/deephunter/refs/heads/main/static/commit_id.txt'

# Max retention (in days). By default 90 days (3 months)
DB_DATA_RETENTION = 90

# Max number of distinct hostnames to consider an analytic as rare
RARE_OCCURRENCES_THRESHOLD = 10

# Threshold for max number of hosts saved to DB for a given analytic (campaigns).
# By default 1000
CAMPAIGN_MAX_HOSTS_THRESHOLD = 1000

# Actions applied to analytics if CAMPAIGN_MAX_HOSTS_THRESHOLD is reached several times
ON_MAXHOSTS_REACHED = {
    "THRESHOLD": 3,
    "DISABLE_RUN_DAILY": True,
    "DELETE_STATS": True
}
# Automatically remove analytic from future campaigns if it failed
DISABLE_RUN_DAILY_ON_ERROR = True

# Analytics per page in the list view
ANALYTICS_PER_PAGE = 50

# Workflow settings
DAYS_BEFORE_REVIEW = 30  # Number of days before an analytic is considered for review
DISABLE_ANALYTIC_ON_REVIEW = False  # Disable analytics with status 'REVIEW'

# Automatically regenerate stats when analytic query field is changed
AUTO_STATS_REGENERATION = True

# Proxy settings
PROXY = {
    'http': 'http://proxy:port',
    'https': 'http://proxy:port'
    }

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
    'connectors',
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


LOGIN_URL = '/admin/login/'

### dbbackup settings (encrypted backups)
DBBACKUP_STORAGE_OPTIONS = {'location': '/data/backups/'}
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
