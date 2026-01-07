"""
Django settings for fieldmax project - PRODUCTION READY
Optimized for Koyeb deployment with PostgreSQL database
"""

import dj_database_url
import sys
from pathlib import Path
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================
from dotenv import load_dotenv
load_dotenv()

# ============================================
# BASE DIRECTORY
# ============================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================
# DEBUG SETTING (MUST BE DEFINED EARLY)
# ============================================
DEBUG = os.getenv("DEBUG", "False") == "True"

# ============================================
# SECURITY SETTINGS
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        # Development fallback - NEVER use in production
        SECRET_KEY = 'django-insecure-dev-key-for-local-testing-only-change-in-production'
        print("⚠️  WARNING: Using development SECRET_KEY. Set SECRET_KEY in Koyeb environment variables.")
    else:
        raise ValueError(
            "SECRET_KEY environment variable is not set! "
            "Please set it in your Koyeb environment variables."
        )

# Koyeb specific domains
KOYEB_APP_NAME = os.getenv("KOYEB_APP_NAME", "fieldmax")
KOYEB_DOMAIN = f"{KOYEB_APP_NAME}-*.koyeb.app"

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', f'.koyeb.app,localhost,127.0.0.1,{KOYEB_APP_NAME}.koyeb.app').split(',')

# ✅ CRITICAL: CSRF Trusted Origins for Koyeb
CSRF_TRUSTED_ORIGINS = [
    "https://*.koyeb.app",
    f"https://{KOYEB_APP_NAME}.koyeb.app",
    f"https://{KOYEB_DOMAIN}",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# ✅ CRITICAL: Proxy SSL Header for Koyeb
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

APPEND_SLASH = True

# ============================================
# INSTALLED APPLICATIONS
# ============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    
    # Cloudinary storage
    'cloudinary_storage',
    'cloudinary',
    
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Django extensions
    'django_extensions',
    
    # REST framework
    'rest_framework',
    'rest_framework.authtoken',
    
    # new apps
    'users.apps.UsersConfig',
    'website.apps.WebsiteConfig',
    'inventory.apps.InventoryConfig',
    'sales.apps.SalesConfig',
]

# ============================================
# MIDDLEWARE
# ============================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'website.middleware.DashboardSessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================
# URL CONFIGURATION
# ============================================
ROOT_URLCONF = 'fieldmax.urls'

# ============================================
# TEMPLATES
# ============================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / "website" / "templates",
            BASE_DIR / "templates",
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',

                # ✅ CUSTOM CONTEXT PROCESSORS
                'website.context_processors.categories_processor',
                'website.context_processors.dashboard_url',
                'website.context_processors.cart_data',
                'inventory.context_processors.categories',
            ],
        },
    },
]

# ============================================
# WSGI APPLICATION
# ============================================
WSGI_APPLICATION = 'fieldmax.wsgi.application'

# ============================================
# DATABASE CONFIGURATION (KOYEB SPECIFIC)
# ============================================
if DEBUG or 'test' in sys.argv or 'runserver' in sys.argv:
    # Local development - SQLite
    print("🔧 Development mode - using SQLite database")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Production - Koyeb PostgreSQL
    # Koyeb provides DATABASE_URL or POSTGRESQL_URL
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRESQL_URL')
    
    if DATABASE_URL:
        print(f"🔗 Using PostgreSQL database from DATABASE_URL")
        DATABASES = {
            'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
        }
    else:
        # Fallback: Check for individual PostgreSQL variables (Koyeb format)
        db_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', os.getenv('PGDATABASE', 'fieldmax')),
            'USER': os.getenv('POSTGRES_USER', os.getenv('PGUSER', 'fieldmax')),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', os.getenv('PGPASSWORD', '')),
            'HOST': os.getenv('POSTGRES_HOST', os.getenv('PGHOST', 'localhost')),
            'PORT': os.getenv('POSTGRES_PORT', os.getenv('PGPORT', '5432')),
        }
        
        # Check if we have PostgreSQL credentials
        if db_config['PASSWORD']:
            DATABASES = {'default': db_config}
            print(f"🔗 Using PostgreSQL: {db_config['HOST']}/{db_config['NAME']}")
        else:
            # Ultimate fallback to SQLite (not recommended for production)
            print("⚠️  WARNING: No PostgreSQL credentials found, falling back to SQLite")
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': BASE_DIR / 'db.sqlite3',
                }
            }

# ============================================
# PASSWORD VALIDATION
# ============================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================
# INTERNATIONALIZATION
# ============================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_L10N = True
USE_TZ = True

USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ','
DECIMAL_SEPARATOR = '.'

# ============================================
# STORAGE CONFIGURATION
# ============================================
# Modern Django storage configuration
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Legacy configuration (for compatibility)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Whitenoise configuration
WHITENOISE_KEEP_ONLY_HASHED_FILES = not DEBUG
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = (
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'zip', 'gz', 'tgz', 
    'bz2', 'tbz', 'xz', 'br', 'swf', 'flv', 'woff', 'woff2',
)

# ============================================
# STATIC FILES (CSS, JavaScript, Images)
# ============================================
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# ============================================
# CLOUDINARY CONFIGURATION
# ============================================
# Configure cloudinary module
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

if all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
    print(f"☁️  Cloudinary configured: {CLOUDINARY_CLOUD_NAME}")
else:
    print("⚠️  Cloudinary credentials missing. Media uploads will fail.")

# ============================================
# MEDIA FILES (User Uploads via Cloudinary)
# ============================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # Fallback for local development

# Maximum upload size (100MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600

# ============================================
# AUTHENTICATION & AUTHORIZATION
# ============================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_AGE = 86400
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# ============================================
# REST FRAMEWORK CONFIGURATION
# ============================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    'TIME_FORMAT': '%H:%M:%S',
}

# ============================================
# INVENTORY MANAGEMENT CONFIGURATION
# ============================================
INVENTORY_CONFIG = {
    'LOW_STOCK_THRESHOLD': 5,
    'CRITICAL_STOCK_THRESHOLD': 2,
    
    'ENABLE_EMAIL_ALERTS': True,
    'ENABLE_SMS_ALERTS': False,
    'LOW_STOCK_ALERT_EMAILS': [
        'fieldmaxlimited@gmail.com',
    ],
    
    'ALLOW_NEGATIVE_STOCK': False,
    'AUTO_GENERATE_CODES': True,
    'REQUIRE_SKU_FOR_SINGLE_ITEMS': True,
    'REQUIRE_PURCHASE_ORDER_REFERENCE': False,
    
    'PRODUCT_CODE_LENGTH': 3,
    'PRODUCT_CODE_PREFIX_LENGTH': 4,
    
    'REQUIRE_STOCK_ENTRY_NOTES': False,
    'REQUIRE_STOCK_ENTRY_REFERENCE': True,
    'MAX_QUANTITY_PER_ENTRY': 10000,
    
    'STOCK_REPORT_DAYS': 30,
    'ENABLE_STOCK_ALERTS': True,
    'ALERT_CHECK_INTERVAL': 3600,
}

# ============================================
# COMPANY INFORMATION
# ============================================
FIELDMAX_COMPANY_NAME = "FIELDMAX SUPPLIERS LTD"
FIELDMAX_COMPANY_SHORT_NAME = "FIELDMAX"
FIELDMAX_ADDRESS = "Nairobi, Kenya"
FIELDMAX_TEL = "+254722558544"
FIELDMAX_EMAIL = "fieldmaxlimited@gmail.com"
FIELDMAX_WEBSITE = "www.fieldmax.co.ke"
FIELDMAX_PIN = "--------"
FIELDMAX_VAT_RATE = 0.16

FIELDMAX_RECEIPT_PREFIX = "RCT"
FIELDMAX_INVOICE_PREFIX = "INV"
FIELDMAX_PURCHASE_ORDER_PREFIX = "PO"
FIELDMAX_RETURN_PREFIX = "RET"

FIELDMAX_BUSINESS_HOURS = {
    'Monday': '08:00-18:00',
    'Tuesday': '08:00-18:00',
    'Wednesday': '08:00-18:00',
    'Thursday': '08:00-18:00',
    'Friday': '08:00-18:00',
    'Saturday': '09:00-17:00',
    'Sunday': 'Closed',
}

# ============================================
# EMAIL CONFIGURATION
# ============================================
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    print("📧 Development mode - using console email backend")
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@fieldmax.co.ke')
    SERVER_EMAIL = DEFAULT_FROM_EMAIL
    
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
        print(f"📧 Email configured: {EMAIL_HOST_USER}")
    else:
        print("⚠️  Email credentials missing. Email functionality disabled.")

# ============================================
# LOGGING CONFIGURATION
# ============================================
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {asctime} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'koyeb': {
            'format': '{asctime} [{levelname}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'koyeb',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'inventory_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'inventory.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'sales_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sales.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'ERROR',
        },
    },
    
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['console', 'inventory_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'sales': {
            'handlers': ['console', 'sales_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ============================================
# CACHING
# ============================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'fieldmax-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# ============================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ============================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# ADMIN CUSTOMIZATION
# ============================================
ADMIN_SITE_HEADER = "FIELDMAX Administration"
ADMIN_SITE_TITLE = "FIELDMAX Admin Portal"
ADMIN_INDEX_TITLE = "Welcome to FIELDMAX Administration"

# ============================================
# SETTINGS VALIDATION
# ============================================
def validate_settings():
    """Validate critical settings on startup"""
    
    errors = []
    warnings = []
    
    # Check Cloudinary credentials
    cloudinary_vars = {
        'CLOUDINARY_CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
        'CLOUDINARY_API_KEY': os.getenv('CLOUDINARY_API_KEY'),
        'CLOUDINARY_API_SECRET': os.getenv('CLOUDINARY_API_SECRET')
    }
    
    missing_cloudinary = [name for name, val in cloudinary_vars.items() if not val]
    
    if missing_cloudinary:
        warnings.append("⚠️  Cloudinary credentials not fully configured!")
        warnings.append(f"   Missing: {', '.join(missing_cloudinary)}")
        warnings.append("   Media uploads will fail. Set these in Koyeb environment variables.")
    else:
        print("✅ Cloudinary configured successfully")
    
    # Check database
    if not DEBUG and DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
        warnings.append("⚠️  Using SQLite in production. Configure PostgreSQL for better performance.")
    
    # Check email configuration
    if INVENTORY_CONFIG['ENABLE_EMAIL_ALERTS'] and not DEBUG:
        if not all([os.getenv('EMAIL_HOST_USER'), os.getenv('EMAIL_HOST_PASSWORD')]):
            warnings.append("⚠️  Email alerts enabled but credentials missing!")
            warnings.append("   Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in Koyeb environment variables.")
    
    # Check static directory
    static_dir = BASE_DIR / "static"
    if not static_dir.exists():
        warnings.append(f"⚠️  Static directory not found: {static_dir}")
        warnings.append("   Create it or remove from STATICFILES_DIRS")
    
    # Check SECRET_KEY in production
    if not DEBUG and SECRET_KEY.startswith('django-insecure-'):
        errors.append("❌ Using development SECRET_KEY in production!")
        errors.append("   Set a proper SECRET_KEY in Koyeb environment variables.")
    
    if errors:
        print("\n" + "="*70)
        print("❌ CRITICAL SETTINGS ERRORS:")
        for error in errors:
            print(f"   {error}")
        print("="*70 + "\n")
    
    if warnings:
        print("\n" + "="*70)
        print("⚠️  SETTINGS WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print("="*70 + "\n")
    
    if not errors and not warnings:
        print("\n✅ All settings validated successfully!\n")

# Run validation on startup
if 'runserver' in sys.argv or 'migrate' in sys.argv or 'collectstatic' in sys.argv:
    validate_settings()

# ============================================
# OFFLINE & SYNC CONFIGURATION
# ============================================
PWA_APP_NAME = 'FieldMax'
PWA_APP_SHORT_NAME = 'FieldMax'
PWA_APP_DESCRIPTION = 'Field Management System with Offline Support'
PWA_APP_THEME_COLOR = '#0066cc'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_START_URL = '/'
PWA_APP_ICONS = [
    {
        'src': '/static/icons/icon-192x192.png',
        'sizes': '192x192',
        'type': 'image/png'
    },
    {
        'src': '/static/icons/icon-512x512.png',
        'sizes': '512x512',
        'type': 'image/png'
    }
]

OFFLINE_STORAGE = {
    'ENABLE_OFFLINE_MODE': True,
    'SYNC_ON_RECONNECT': True,
    'QUEUE_REQUESTS_OFFLINE': True,
    'MAX_OFFLINE_STORAGE': 50,
    'OFFLINE_DATA_RETENTION_DAYS': 7,
    'SYNC_RETRY_ATTEMPTS': 3,
    'SYNC_RETRY_DELAY': 5,
    'OFFLINE_CAPABILITIES': {
        'view_inventory': True,
        'create_sale': True,
        'update_stock': True,
        'view_reports': True,
        'create_customer': True,
    },
    'CONFLICT_RESOLUTION': 'server_wins',
    'ENABLE_BACKGROUND_SYNC': True,
}

OFFLINE_ENABLED_ENDPOINTS = [
    '/api/inventory/',
    '/api/sales/',
    '/api/customers/',
    '/api/products/',
]

SYNC_NOTIFICATIONS = {
    'ENABLE_NOTIFICATIONS': True,
    'NOTIFY_ON_SYNC_START': False,
    'NOTIFY_ON_SYNC_COMPLETE': True,
    'NOTIFY_ON_SYNC_ERROR': True,
}

# ============================================
# FINAL STARTUP MESSAGE
# ============================================
print(f"\n🚀 FieldMax initialized successfully!")
print(f"   Environment: {'DEVELOPMENT' if DEBUG else 'PRODUCTION'}")
print(f"   Database: {DATABASES['default']['ENGINE']}")
print(f"   Allowed Hosts: {ALLOWED_HOSTS}")
print("="*50 + "\n")