from .base import *
import os

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# あとでPostgreSQLにするならここを変更
# DATABASES = {
#     "default": dj_database_url.config(
#         default=os.getenv("DATABASE_URL"),
#         conn_max_age=600,
#     )
# }

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True