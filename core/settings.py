"""
Django settings for core project.
"""

import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-test-key')

# SECURITY WARNING: don't run with debug turned on in production!
# Na Renderi nastavíme Environment Variable DEBUG = False
DEBUG = True

# --- DOMÉNY A HOSTING (OPRAVENÉ) ---

# Základné domény
ALLOWED_HOSTS = ['*']

# Pridáme dynamické domény z Renderu (pre istotu)
render_hosts = os.environ.get('ALLOWED_HOSTS')
if render_hosts:
    ALLOWED_HOSTS.extend(render_hosts.split(','))
else:
    # Fallback pre subdomény onrender
    ALLOWED_HOSTS.append('.onrender.com')

# DÔLEŽITÉ PRE RENDER: Aby Django vedelo, že je na HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Toto je DÔLEŽITÉ pre formuláre na vlastnej doméne
CSRF_TRUSTED_ORIGINS = [
    'https://jefi.sk',
    'https://www.jefi.sk',
    'https://*.onrender.com'
]

# --- APLIKÁCIE ---

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'products',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Pre statické súbory na produkcii
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# --- DATABÁZA ---

DATABASES = {
    'default': dj_database_url.config(
        # Lokálne použije sqlite, na Renderi použije PostgreSQL
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        conn_max_age=600
    )
}

# --- HESLÁ ---

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- JAZYK A ČAS (Slovensko) ---

LANGUAGE_CODE = 'sk'
TIME_ZONE = 'Europe/Bratislava'
USE_I18N = True
USE_TZ = True

# --- STATICKÉ SÚBORY (CSS, JS, Images) ---

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# TOTO JE KĽÚČOVÉ PRE OPRAVU CHYBY 500 (Nemenit na Manifest!):
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# --- AUTENTIFIKÁCIA A PRESMEROVANIA ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'

# --- ODOSIELANIE E-MAILOV (Brevo / SMTP) ---

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'info@jefi.sk'