from pathlib import Path
from django.utils.translation import gettext_lazy as _
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ========= Security / Env =========
# Renderなど本番では必ず環境変数で上書きする
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "1") == "1"

# Render が自動で用意するホスト名（ある場合）
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

# 環境変数から ALLOWED_HOSTS を読む（カンマ区切り）
# 例: ALLOWED_HOSTS="example.onrender.com,localhost,127.0.0.1"
if DEBUG:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
else:
    ALLOWED_HOSTS = ["django-5min-languageapp.onrender.com"]

CSRF_TRUSTED_ORIGINS = ["https://django-5min-languageapp.onrender.com"]

# Renderのホスト名を必ず許可（envが空でも動くように）
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# 念のため：あなたのRender URL（固定で許可）
ALLOWED_HOSTS.append("django-5min-languageapp.onrender.com")

# CSRF（本番でフォームPOSTするときに必要）
# 例: CSRF_TRUSTED_ORIGINS="https://example.onrender.com"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = ["https://django-5min-languageapp.onrender.com"]


# ========= Apps =========
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

# ========= Middleware =========
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # static配信用
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "quicklesson.urls"

# ========= Templates =========
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "quicklesson.wsgi.application"
ASGI_APPLICATION = "quicklesson.asgi.application"

# ========= Database =========
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ========= Password validation =========
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ========= i18n =========
LANGUAGE_CODE = "ja"
TIME_ZONE = "Europe/Zurich"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("ja", _("Japanese")),
    ("en", _("English")),
    ("es", _("Spanish")),
    ("fr", _("French")),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# ========= Static files =========
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise: 余裕があれば圧縮＆キャッシュ強化（任意）
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ========= Auth redirects =========
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
