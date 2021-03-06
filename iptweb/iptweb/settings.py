"""
Django settings for iptweb project.

Generated by 'django-admin startproject' using Django 1.11.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '-----&ye!5y&(ud*ci#r#(02h1j8mx$1-tv9erf!y*e-------'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['ipt-web.tacc.utexas.edu', 'ipt.tacc.cloud', 'ipt.tacc.cloud.local']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'bootstrap3',
    'nocaptcha_recaptcha',

    'iptsite',
    'messageBoard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

ROOT_URLCONF = 'iptweb.urls'


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
            ],
        },
    },
]

WSGI_APPLICATION = 'iptweb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Chicago'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'iptsite'),
#     '/static/',
# ]

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/iptweb/iptsite/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/iptweb/iptsite/media/'

# LOGIN_REDIRECT_URL = '/' # means home view


# set to false to skip calls to the actor
CALL_ACTOR = True

# list of users capable of reaching the admin URL
ADMIN_USERS = ['jstubbs', 'mlm55', 'rauta']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[DJANGO] %(levelname)s %(asctime)s %(module)s %(name)s.%(funcName)s:%(lineno)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True,
        },
        'iptsite': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

#Various settings
AGAVE_STORAGE_SYSTEM_ID = os.environ.get('AGAVE_STORAGE_SYSTEM_ID', 'dev.ipt.cloud.storage')

STAMPEDE_RUN_APP_VERSION = os.environ.get("STAMPEDE_RUN_APP_VERSION", "ipt-run-stampede-0.1.0")
LS5_RUN_APP_VERSION = os.environ.get("LS5_RUN_APP_VERSION", "ipt-run-ls5-0.1.0")
COMET_RUN_APP_VERSION = os.environ.get("COMET_RUN_APP_VERSION", "ipt-run-comet-0.1.0")

STAMPEDE_BUILD_APP_VERSION = os.environ.get("STAMPEDE_BUILD_APP_VERSION", "ipt-build-stampede-0.1.0")
LS5_BUILD_APP_VERSION = os.environ.get("LS5_BUILD_APP_VERSION", "ipt-build-ls5-0.1.0")
COMET_BUILD_APP_VERSION = os.environ.get("COMET_BUILD_APP_VERSION", "ipt-build-comet-0.1.0")

TAS_CLIENT_KEY = os.environ.get("TAS_CLIENT_KEY", "tasclient")
TAS_CLIENT_SECRET = os.environ.get("TAS_CLIENT_SECRET", "password")
TAS_URL = os.environ.get("TAS_URL", "example.api")

NORECAPTCHA_SITE_KEY = os.environ.get("NORECAPTCHA_SITE_KEY", "sitekey")
NORECAPTCHA_SECRET_KEY = os.environ.get("NORECAPTCHA_SITE_KEY", "sitesecret")
