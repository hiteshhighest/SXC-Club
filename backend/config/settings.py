import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Neon writes branch credentials to the repository root. Load those first, then
# retain the backend-local .env as a fallback for existing local setups.
load_dotenv(BASE_DIR.parent / ".env.local")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-this-secret-before-deploying")
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("dev-only-") or SECRET_KEY.startswith("replace-with-")):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a private random value of at least 50 characters when DEBUG is false.")

def env_list(name, default=""):
    return [value.strip().rstrip("/") for value in os.getenv(name, default).split(",") if value.strip()]

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "corsheaders", "clubs",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
primary_database_url = os.getenv("DATABASE_URL")
management_command = sys.argv[1] if len(sys.argv) > 1 else ""
use_sqlite = os.getenv("DJANGO_USE_SQLITE", "true" if DEBUG else "false").lower() == "true"
if not DEBUG and use_sqlite:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("DJANGO_USE_SQLITE cannot be enabled when DJANGO_DEBUG is false.")
if management_command == "test":
    # Never point Django's disposable test database at the configured production DB.
    selected_database_url = os.getenv("DJANGO_TEST_DATABASE_URL")
elif use_sqlite:
    selected_database_url = None
elif primary_database_url:
    # Use Neon’s pooled URL for normal requests and its direct URL for schema
    # operations, which need session-level migration locks.
    from urllib.parse import parse_qs, urlparse, unquote
    migration_commands = {"migrate", "makemigrations", "showmigrations", "test"}
    unpooled_database_url = os.getenv("DATABASE_URL_UNPOOLED") if management_command in migration_commands else None
    selected_database_url = unpooled_database_url or primary_database_url
else:
    selected_database_url = None

if selected_database_url:
    from urllib.parse import parse_qs, urlparse, unquote
    db = urlparse(selected_database_url)
    query_options = {key: values[-1] for key, values in parse_qs(db.query).items() if values}
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": db.path.lstrip("/"),
        "USER": unquote(db.username or ""), "PASSWORD": unquote(db.password or ""), "HOST": db.hostname,
        "PORT": db.port or 5432, "CONN_MAX_AGE": 60, "OPTIONS": query_options}}
else:
    if not DEBUG and management_command != "test":
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("DATABASE_URL is required when DJANGO_DEBUG is false.")
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/minute", "user": "180/minute", "login": "10/minute"},
}
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", ",".join(CORS_ALLOWED_ORIGINS))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")
if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured
    missing_origins = [name for name, values in (
        ("CORS_ALLOWED_ORIGINS", CORS_ALLOWED_ORIGINS),
        ("CSRF_TRUSTED_ORIGINS", CSRF_TRUSTED_ORIGINS),
    ) if not values]
    if missing_origins:
        raise ImproperlyConfigured(f"Set {', '.join(missing_origins)} to the deployed frontend origin(s).")
    if not FRONTEND_URL.startswith("https://"):
        raise ImproperlyConfigured("Set FRONTEND_URL to the deployed HTTPS frontend origin.")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "SXC Clubs <noreply@sxc-clubs.local>")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax" if DEBUG else "None")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax" if DEBUG else "None")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
