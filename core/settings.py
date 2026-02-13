"""
Django settings for core project.
"""

import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-x^7!)5a$1+qia1@w*5d47&ke*rrd$fm3!l7ez8l8lntc1*!rf8')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# --- DOMÉNY A HOSTING ---

ALLOWED_HOSTS = [
    'jefi.sk',
    'www.jefi.sk',
    '127.0.0.1',
    'localhost'
]

# Automatické pridanie domén z Renderu
render_hosts = os.environ.get('ALLOWED_HOSTS')
if render_hosts:
    ALLOWED_HOSTS.extend(render_hosts.split(','))
else:
    # Fallback pre subdomény onrender
    ALLOWED_HOSTS.append('.onrender.com')

# DÔLEŽITÉ PRE RENDER: Aby Django vedelo, že je na HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
    'django.contrib.staticfiles', # Toto je nutné pre CSS
    'django.contrib.sitemaps',
    'products',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # 👈 MUSÍ BYŤ HNEĎ PO SECURITY
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
        'DIRS': [BASE_DIR / 'templates'], 
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
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
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

# --- STATICKÉ SÚBORY (KĽÚČOVÉ PRE DIZAJN) ---

STATIC_URL = '/static/'

# Kam sa uložia súbory pri 'python manage.py collectstatic' (pre Render)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Kde má Django hľadať tvoj output.css (lokálne)
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Optimalizácia pre Render (WhiteNoise)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# --- AUTENTIFIKÁCIA A PRESMEROVANIA ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'

# --- EMAIL ---

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'info@jefi.sk'

# --- CJ AFFILIATE ---
CJ_WEBSITE_ID = "101646612"
CJ_DEVELOPER_KEY = "O2uledg8fW-ArSOgXxt2jEBB0Q"