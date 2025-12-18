import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "schools",
    "documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.SimpleCorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Abidjan"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_DEFAULT_QUEUE = "documents"
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "0") == "1"
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.environ.get("CELERY_WORKER_PREFETCH_MULTIPLIER", "2"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "60"))
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "75"))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.environ.get("CELERY_WORKER_MAX_TASKS_PER_CHILD", "100"))
CELERY_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "7"))
PURGE_EXPIRED_EVERY_SECONDS = int(os.environ.get("PURGE_EXPIRED_EVERY_SECONDS", "3700"))  # 0 = désactivé
PURGE_EXPIRED_HOURS = int(os.environ.get("PURGE_EXPIRED_HOURS", "1"))  # seuil d'âge pour purge auto

XELATEX_BIN = os.environ.get("XELATEX_BIN", "xelatex")
LATEX_LOG_DIR = Path(os.environ.get("LATEX_LOG_DIR", "")) if os.environ.get("LATEX_LOG_DIR") else None
LATEX_TMP_DIR = os.environ.get("LATEX_TMP_DIR") or None
LATEX_DEFAULT_PASSES = int(os.environ.get("LATEX_DEFAULT_PASSES", "2"))

LATEX_TEMPLATES = {
    "BULLETIN": BASE_DIR / "templates_latex" / "bulletin.tex",
    "HONOR": BASE_DIR / "templates_latex" / "tableau_honneur.tex",
}

LATEX_THEME_FILES = {
    "BULLETIN": Path(os.environ.get("BULLETIN_THEME_FILE", BASE_DIR / "config/themes/bulletin_theme.json")),
    "HONOR": Path(os.environ.get("HONOR_THEME_FILE", BASE_DIR / "config/themes/honor_theme.json")),
}

DOCUMENT_STORAGE = os.environ.get("DOCUMENT_STORAGE", "local")  # local or s3
DOCUMENT_BASE_URL = os.environ.get("DOCUMENT_BASE_URL", "http://localhost:8000/media/documents/")
DOCUMENT_STORAGE_PATH = Path(os.environ.get("DOCUMENT_STORAGE_PATH", MEDIA_ROOT / "documents"))
DOCUMENT_TTL_SECONDS = int(os.environ.get("DOCUMENT_TTL_SECONDS", "900"))  # défaut 30 min

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL")
AWS_REGION = os.environ.get("AWS_REGION")

# Planification Celery Beat (optionnelle) pour purger les fichiers expirés
CELERY_BEAT_SCHEDULE = {}
if PURGE_EXPIRED_EVERY_SECONDS > 0:
    CELERY_BEAT_SCHEDULE["purge-expired-docs"] = {
        "task": "documents.tasks.purge_expired",
        "schedule": PURGE_EXPIRED_EVERY_SECONDS,
        "args": (PURGE_EXPIRED_HOURS,),
    }
