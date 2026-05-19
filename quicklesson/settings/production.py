from .base import *
import os
import dj_database_url
DEBUG = False

ALLOWED_HOSTS = [
    "django-5min-languageapp.onrender.com",
]

RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    "https://django-5min-languageapp.onrender.com",
]

env_csrf = os.getenv("CSRF_TRUSTED_ORIGINS")

if env_csrf:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in env_csrf.split(",")
        if origin.strip()
    ]

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is not set")

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    )
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True