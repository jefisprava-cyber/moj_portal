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
# Na Renderi nastavíme Environment Variable DEBUG = False
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# --- DOMÉNY A HOSTING ---

ALLOWED_HOSTS = [
    'jefi.sk',
    'www.jefi.sk',
    '.onrender.com', # Povolí všetky subdomény na Renderi
    '127.0.0.1',
    'localhost'
]

# Toto je DÔLEŽITÉ pre formuláre na vlastnej doméne (aby fungoval Login a Ukladanie)
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
        # Lokálne použije sqlite, na Renderi použije PostgreSQL (cez premennú DATABASE_URL)
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

LANGUAGE_CODE = 'sk' # Zmenené na slovenčinu

TIME_ZONE = 'Europe/Bratislava' # Zmenené na náš čas

USE_I18N = True
USE_TZ = True

# --- STATICKÉ SÚBORY (CSS, JS, Images) ---

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- AUTENTIFIKÁCIA A PRESMEROVANIA ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'