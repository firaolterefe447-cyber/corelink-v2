import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _
import django.conf.locale
from dotenv import load_dotenv

# ==============================================
# 0. BASE DIRECTORY SETUP
# ==============================================
# Resolves the absolute path to the project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# ==============================================
# 1. ENVIRONMENT DETECTION (CRITICAL)
# ==============================================
# We detect HahuCloud by checking if the 'corelink' system user directory exists.
# This allows the same file to work on your PC (Local) and the Server (Production).
IS_HAHU = os.path.exists("/home/corelink")

# ==============================================
# 2. SECURITY CONFIGURATION
# ==============================================
# In production, we fetch the secret key from environment variables for safety.
# Locally, it falls back to a development key.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-corelink-nexus-v1-development-only"
)

# DEBUG is automatically DISABLED on the server to prevent exposing code details.
DEBUG = not IS_HAHU

# Explicitly defining which domains/IPs can access this Django app.
ALLOWED_HOSTS = [
    "corelink.et",
    "www.corelink.et",
    "91.204.209.4",
    "localhost",
    "127.0.0.1",
]

# Security requirement for modern Django versions when using forms/admin over HTTPS
CSRF_TRUSTED_ORIGINS = ["https://corelink.et", "https://www.corelink.et"]

# ==============================================
# 3. APPLICATION DEFINITIONS
# ==============================================
INSTALLED_APPS = [
    # Premium Admin Theme (Must be above django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    # Core Django Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-Party Optimization Tools
    "tailwind",
    "theme",
    "django_browser_reload",
    "imagekit",
    "django_htmx",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Custom Project Modules
    "core",
    "accounts.apps.AccountsConfig",
    "profiles",
    "workspace",
    "operations",
    "content",
    "network.apps.NetworkConfig",
    "subscriptions.apps.SubscriptionsConfig",
    "watson",
    "opportunities",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Whitenoise handles static file compression and caching for fast loading
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "accounts.middleware.EmailVerificationRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "theme" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Update this line to use the new function name:
                "profiles.context_processors.role_and_company_context",
                "workspace.context_processors.unread_notifications",
            ],
        },
    },
]
# ==============================================
# 4. DATABASE CONFIGURATION (POSTGRESQL)
# ==============================================
if IS_HAHU:
    # PRODUCTION: Using the PostgreSQL database created in cPanel
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "corelink_corelink_db"),
            "USER": os.getenv("DB_USER", "corelink_firaol"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
elif os.getenv("USE_SQLITE") == "True":
    # LOCAL: Using SQLite if requested
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # LOCAL: Default to PostgreSQL
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "corelink_corelink_db"),
            "USER": os.getenv("DB_USER", "corelink_firaol"),
            "PASSWORD": os.getenv("DB_PASSWORD", "corelink_firaol7744$*#"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

# ==============================================
# 5. AUTHENTICATION & LOCALIZATION
# ==============================================
AUTH_PASSWORD_VALIDATORS = (
    []
)  # Keeping simple for now; recommended to enable in final stage
AUTH_USER_MODEL = "accounts.CustomUser"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_ADAPTER = "accounts.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.CustomSocialAccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            "secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            "key": "",
        },
    }
}

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", _("English")),
    ("am", _("Amharic")),
    ("om", _("Oromo")),
]

# 1. Define metadata for BOTH Amharic and Oromo
EXTRA_LANG_INFO = {
    "am": {
        "bidi": False,
        "code": "am",
        "name": "Amharic",
        "name_local": "አማርኛ",
    },
    "om": {
        "bidi": False,
        "code": "om",
        "name": "Oromo",
        "name_local": "Afaan Oromoo",
    },
}

# 2. Inject it into Django's global locale info permanently
django.conf.locale.LANG_INFO.update(EXTRA_LANG_INFO)

# 3. Create a folder path for translation files
LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

# ==============================================
# 6. STATIC AND MEDIA ASSETS (HAHU NATIVE)
# ==============================================
# STATIC: For CSS, JS, and project-wide logos
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "theme/static")]

# MEDIA: For user-uploaded images and dynamic hero banners
MEDIA_URL = "/media/"

if IS_HAHU:
    # On HahuCloud, assets must be in public_html to be accessible via the web
    STATIC_ROOT = "/home/corelink/public_html/static"
    MEDIA_ROOT = "/home/corelink/public_html/media"
else:
    # On your PC, assets are kept in the project folder
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Efficient storage management for production
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# ==============================================
# 7. TAILWIND & ADMIN THEME CONFIGURATION
# ==============================================
TAILWIND_APP_NAME = "theme"
# Automatically detects if Node.js is needed based on environment
NPM_BIN_PATH = None if IS_HAHU else r"C:\Program Files\nodejs\npm.cmd"

UNFOLD = {
    "DASHBOARD_CALLBACK": "core.dashboard.dashboard_callback",
    "SITE_TITLE": "CoreLink Nexus",
    "SITE_HEADER": "CORE.LINK",
    "SITE_URL": "/",
    # COLORS configuration
    "COLORS": {
        "primary": {
            "50": "236 253 245",
            "100": "209 250 229",
            "200": "167 243 208",
            "300": "110 231 183",
            "400": "52 211 153",
            "500": "16 185 129",
            "600": "5 150 105",
            "700": "4 120 87",
            "800": "6 95 70",
            "900": "6 78 59",
            "950": "2 44 34",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Global Command"),
                "separator": True,
                "items": [
                    {"title": _("Dashboard"), "icon": "dashboard", "link": "/admin/"},
                    {
                        "title": _("User Registry"),
                        "icon": "group",
                        "link": "/admin/accounts/customuser/",
                    },
                ],
            },
            {
                "title": _("Talent Ecosystem"),
                "separator": True,
                "items": [
                    {
                        # UNIFIED: One link to rule them all instead of 3 fragmented tables
                        "title": _("Unified Portfolios"),
                        "icon": "account_box",
                        "link": "/admin/profiles/userprofile/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Companies (Founders)"),
                        "icon": "business",
                        "link": "/admin/profiles/company/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Inbound Streams"),
                "separator": True,
                "items": [
                    {
                        "title": _("Applications"),
                        "icon": "approval",
                        "link": "/admin/accounts/applicationrequest/",
                        "badge": "action",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Volunteers"),
                        "icon": "volunteer_activism",
                        "link": "/admin/accounts/communitycontributor/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Live Operations View"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Browse Users"),
                        "icon": "manage_search",
                        "link": "/ops/pool/USER/",
                        "badge": "View Mode",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Browse Companies"),
                        "icon": "business",
                        "link": "/ops/pool/COMPANY/",
                        "badge": "View Mode",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Security HQ"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Blackbox Ledger"),
                        "icon": "visibility",
                        "link": "/admin/operations/auditlog/",
                        "badge": "Top Secret",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Staff Control"),
                        "icon": "admin_panel_settings",
                        "link": "/admin/accounts/customuser/?is_staff__exact=1",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },
    "TABS": [
        {
            "models": ["accounts.customuser"],
            "items": [
                {"title": _("Identity & Role"), "link": "#identity"},
                {"title": _("Security & Access"), "link": "#security"},
                {"title": _("Permissions"), "link": "#permissions"},
                {"title": _("Associations"), "link": "#associations"},
            ],
        },
        {
            # UNIFIED: Pointing the tabs to the new model
            "models": ["profiles.userprofile"],
            "items": [
                {"title": _("Profile Overview"), "link": "#overview"},
                {"title": _("Professional Intent"), "link": "#intent"},
                {"title": _("Algorithm & Rating"), "link": "#scoring"},
            ],
        },
    ],
}
# ==============================================
# 8. ACCESS CONTROL REDIRECTS
# ==============================================
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================
# 9. TELEGRAM BOT SETTINGS
# ==============================================
TELEGRAM_BOT_TOKEN = "8233897962:AAFgzSfOQCj6RJAp3P4PT1j-AQRA1roFQJA"
TELEGRAM_WEBHOOK_URL = "https://corelink.et/telegram-webhook/"
