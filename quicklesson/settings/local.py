from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Read only the local API credential; process environment takes precedence.
if not OPENAI_API_KEY:
    _key_file = BASE_DIR / ".env.local"
    if _key_file.is_file():
        for _line in _key_file.read_text().splitlines():
            if _line.startswith("OPENAI_API_KEY="):
                OPENAI_API_KEY = _line.split("=", 1)[1].strip().strip("\"'")
                break
