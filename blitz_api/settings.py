"""
Django settings for Blitz-API project.

Generated by 'django-admin startproject' using Django 2.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

from ast import literal_eval
import logging
from pathlib import Path
import sys

from decouple import config, Csv
from django.utils.translation import ugettext_lazy as _
from dj_database_url import parse as db_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).absolute().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

# Application definition

INSTALLED_APPS = [
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'blitz_api',
    'workplace',
    'store',
    'retirement',
    'log_management',
    'cron_manager',
    'ckeditor_api',
    'storages',
    'anymail',
    'simple_history',
    'safedelete',
    'import_export',
    'django_filters',
    'admin_auto_filters',
    'django_admin_inline_paginator',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'request_logging.middleware.LoggingMiddleware',  # logs requests body
]

# django-request-logging settings

REQUEST_LOGGING_HTTP_4XX_LOG_LEVEL = logging.WARNING

# Django logging configuration

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'email_backend': 'django.core.mail.backends.smtp.EmailBackend',
            'include_html': True,
            'filters': [],
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',  # change debug level as appropiate
            'propagate': False,
        },
    },
}
# Disable logging during unittests. Can be overriden in specific tests with:
#   import logging
#   logging.disable(logging.NOTSET)
if len(sys.argv) > 1 and sys.argv[1] == 'test':
    logging.disable(logging.CRITICAL)

ROOT_URLCONF = 'blitz_api.urls'

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

WSGI_APPLICATION = 'blitz_api.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': config(
        'DATABASE_URL',
        default='sqlite:///' + str(BASE_DIR.joinpath('db.sqlite3')),
        cast=db_url
    )
}

# Custom user model

AUTH_USER_MODEL = 'blitz_api.User'

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-ca'

TIME_ZONE = 'America/Montreal'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LANGUAGES = [
    ('fr', _('French')),
    ('en', _('English')),
]

# File upload size
DATA_UPLOAD_MAX_MEMORY_SIZE = config('DATA_UPLOAD_MAX_MEMORY_SIZE',
                                     default=2621440, cast=int)
FILE_UPLOAD_MAX_MEMORY_SIZE = config('FILE_UPLOAD_MAX_MEMORY_SIZE',
                                     default=2621440, cast=int)

# AWS Deployment configuration (with Zappa)
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ca-central-1')
AWS_STORAGE_STATIC_BUCKET_NAME = config('AWS_STORAGE_STATIC_BUCKET_NAME',
                                        default='example_static')
AWS_STORAGE_MEDIA_BUCKET_NAME = config('AWS_STORAGE_MEDIA_BUCKET_NAME',
                                       default='example_media')
AWS_S3_STATIC_CUSTOM_DOMAIN = config('AWS_S3_STATIC_CUSTOM_DOMAIN',
                                     default='example_static.s3.region.amazonaws.com')
AWS_S3_MEDIA_CUSTOM_DOMAIN = config('AWS_S3_MEDIA_CUSTOM_DOMAIN',
                                    default='example_media.s3.region.amazonaws.com')
AWS_S3_STATIC_DIR = config('AWS_S3_STATIC_DIR', default='static')
AWS_S3_MEDIA_DIR = config('AWS_S3_MEDIA_DIR', default='media')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/
# Force local storage for unittests. Temporary.
if len(sys.argv) > 1 and sys.argv[1] == 'test':
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATIC_URL = config('STATIC_URL', default='/static/')
    STATICFILES_STORAGE = config('STATICFILES_STORAGE',
                                 default='django.contrib.staticfiles.storage.StaticFilesStorage')
if STATICFILES_STORAGE == 'django.contrib.staticfiles.storage.StaticFilesStorage':
    STATIC_ROOT = 'static/'

# User uploaded files (MEDIA)
MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default='media/')
DEFAULT_FILE_STORAGE = config(
    'DEFAULT_FILE_STORAGE',
    default='django.core.files.storage.FileSystemStorage')

# Django Rest Framework

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'blitz_api.authentication.TemporaryTokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter'
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.'
                                'LimitOffsetPagination',
    'PAGE_SIZE': 100
}

# CORS Header Django Rest Framework

CORS_ORIGIN_ALLOW_ALL = True
CORS_EXPOSE_HEADERS = ["Link", ]

# Temporary Token

REST_FRAMEWORK_TEMPORARY_TOKENS = {
    'MINUTES': config('TEMPORARY_TOKEN_MINUTES', default=30, cast=int),
    'RENEW_ON_SUCCESS': config('TEMPORARY_TOKEN_RENEW_ON_SUCCESS',
                               default=True, cast=bool),
    'USE_AUTHENTICATION_BACKENDS': config('USE_AUTHENTICATION_BACKENDS',
                                          default=False, cast=bool),
}

# Activation Token

ACTIVATION_TOKENS = {
    'MINUTES': config('ACTIVATION_TOKENS_MINUTES', default=1440, cast=int),
}

# Email service configuration (using Anymail).
# Refer to Anymail's documentation for configuration details.

ANYMAIL = {
    'SENDINBLUE_API_KEY': config('SENDINBLUE_API_KEY', default='example_key'),
    'REQUESTS_TIMEOUT': config('REQUESTS_TIMEOUT', default=(30, 30),
                               cast=tuple),
    'TEMPLATES': {
        'CONFIRM_SIGN_UP': config(
            'CONFIRM_SIGN_UP',
            default='0',
            cast=int
        ),
        'FORGOT_PASSWORD': config(
            'FORGOT_PASSWORD',
            default='0',
            cast=int
        ),
        'RESERVATION_CANCELLED': config(
            'RESERVATION_CANCELLED',
            default='0',
            cast=int
        ),
        'CONFIRM_CHANGE_EMAIL': config(
            'CONFIRM_CHANGE_EMAIL',
            default='0',
            cast=int
        ),
        'THROWBACK_VIRTUAL_RETREAT': config(
            'TEMPLATE_EMAIL_THROWBACK_VIRTUAL_RETREAT',
            default='14',
            cast=int
        ),
        'THROWBACK_PHYSICAL_RETREAT': config(
            'TEMPLATE_EMAIL_THROWBACK_PHYSICAL_RETREAT',
            default='0',
            cast=int
        ),
        'REMINDER_PHYSICAL_RETREAT': config(
            'TEMPLATE_EMAIL_REMINDER_PHYSICAL_RETREAT',
            default='0',
            cast=int
        ),
        'REMINDER_VIRTUAL_RETREAT': config(
            'TEMPLATE_EMAIL_REMINDER_VIRTUAL_RETREAT',
            default='11',
            cast=int
        ),
        'WELCOME_PHYSICAL_RETREAT': config(
            'TEMPLATE_EMAIL_WELCOME_PHYSICAL_RETREAT',
            default='0',
            cast=int
        ),
        'WELCOME_VIRTUAL_RETREAT': config(
            'TEMPLATE_EMAIL_WELCOME_VIRTUAL_RETREAT',
            default='12',
            cast=int
        ),
        'RENEW_MEMBERSHIP': config(
            'RENEW_MEMBERSHIP',
            default='31',
            cast=int
        )
    },
}
EMAIL_BACKEND = config('EMAIL_BACKEND',
                       default='django.core.mail.backends.smtp.EmailBackend')
# This 'FROM' email is not used with SendInBlue templates
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL',
                            default='noreply@example.org')

# Django email service. Used for administrative emails.

EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='example@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='password')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
# Email addresses to notify in case of error
ADMINS = config('ADMINS', default="",
                cast=lambda v: literal_eval("[" + v + "]"))
SERVER_EMAIL = config('SERVER_EMAIL', default='example@gmail.com')
SUPPORT_EMAIL = config('SUPPORT_EMAIL', default='admin@fjnr.ca')

# User specific settings

LIMIT_DATE_FOR_FREE_VIRTUAL_RETREAT_ON_MEMBERSHIP = config(
    'LIMIT_DATE_FOR_FREE_VIRTUAL_RETREAT_ON_MEMBERSHIP',
    default='1990-01-01',
)

LOCAL_SETTINGS = {
    'ORGANIZATION': config(
        'ORGANIZATION',
        default='Blitz',
    ),
    'EMAIL_SERVICE': config(
        'EMAIL_SERVICE',
        default=False,
        cast=bool,
    ),
    'AUTO_ACTIVATE_USER': config(
        'AUTO_ACTIVATE_USER',
        default=False,
        cast=bool,
    ),
    'FRONTEND_INTEGRATION': {
        'LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT': config(
            'LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT',
            default='https://www.thesez-vous.com/sypreparer_retraitevirtuelle.html',
        ),
        'PROFILE_URL': config(
            'PROFILE_URL',
            default='https://www.thesez-vous.org/profile',
        ),
        'POLICY_URL': config(
            'POLICY_URL',
            default='https://www.thesez-vous.com/politiquesannulation.html',
        ),
        'ACTIVATION_URL': config(
            'ACTIVATION_URL',
            default='https://example.com/activate/{{token}}',
        ),
        'EMAIL_CHANGE_CONFIRMATION': config(
            'EMAIL_CHANGE_CONFIRMATION',
            default='https://example.com/validate/email/{{token}}'
        ),
        'FORGOT_PASSWORD_URL': config(
            'FORGOT_PASSWORD_URL',
            default='https://example.com/reset-password/{{token}}',
        ),
        'RETREAT_INVITATION_URL': config(
            'RETREAT_INVITATION_URL',
            default='https://example.com/retreat_invitation/{{token}}',
        ),
        'RETREAT_UNSUBSCRIBE_URL': config(
            'RETREAT_UNSUBSCRIBE_URL',
            default='https://example.com/wait_queue/{{wait_queue_id}}/unsubscribe',
        ),
    },
    'SELLING_TAX': 0.14975,
    'RETREAT_NOTIFICATION_LIFETIME_DAYS': config(
        'RETREAT_NOTIFICATION_LIFETIME_DAYS',
        default=30,
    ),
}

# Payment settings

PAYSAFE = {
    'ACCOUNT_NUMBER': config('PAYSAFE_ACCOUNT_NUMBER', default='1234567890'),
    'USER': config('PAYSAFE_USER', default='user'),
    'PASSWORD': config('PAYSAFE_PASSWORD', default='password'),
    'BASE_URL': config('PAYSAFE_BASE_URL',
                       default='https://api.test.paysafe.com/'),
    'VAULT_URL': config('PAYSAFE_VAULT_URL', default='customervault/v1/'),
    'CARD_URL': config('PAYSAFE_CARD_URL', default='cardpayments/v1/'),
}

# django-import-export

IMPORT_EXPORT_USE_TRANSACTIONS = True

# External scheduler
EXTERNAL_SCHEDULER = {
    'URL': config('EXTERNAL_SCHEDULER_URL', default='http://example.com'),
    'USER': config('EXTERNAL_SCHEDULER_USER', default='user'),
    'PASSWORD': config('EXTERNAL_SCHEDULER_PASSWORD', default='password'),
    'URL_TO_CALL': config('URL_TO_CALL', default='http://example.com'),
}

MAILCHIMP_API_KEY = config('MAILCHIMP_API_KEY', default='')
MAILCHIMP_SUBSCRIBE_LIST_ID = config(
    'MAILCHIMP_SUBSCRIBE_LIST_ID', default='')
MAILCHIMP_ENABLED = config(
    'MAILCHIMP_ENABLED', default=False, cast=bool)
