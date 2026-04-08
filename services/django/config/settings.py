from decouple import config
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [host for host in config("DJANGO_ALLOWED_HOSTS", default="*").split(",") if host]
USE_SQLITE = config("USE_SQLITE", default=False, cast=bool)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "pgvector",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "social_django",
    "corsheaders",
    "users",
    "pets",
    "products",
    "orders",
    "chat",
    "recommendations",
]

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.kakao.KakaoOAuth2",
    "social_core.backends.naver.NaverOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "social_django.context_processors.backends",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if USE_SQLITE:
    SQLITE_NAME = config("SQLITE_NAME", default=str(Path("/tmp") / "SKN22-129-db.sqlite3"))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_NAME,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB"),
            "USER": config("POSTGRES_USER"),
            "PASSWORD": config("POSTGRES_PASSWORD"),
            "HOST": config("POSTGRES_HOST", default="postgres"),
            "PORT": config("POSTGRES_PORT", default="5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "BLACKLIST_AFTER_ROTATION": True,
}

SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("DJANGO_SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("DJANGO_CSRF_COOKIE_SECURE", default=False, cast=bool)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    origin for origin in config("DJANGO_CSRF_TRUSTED_ORIGINS", default="").split(",") if origin
]

CORS_ALLOWED_ORIGINS = [origin for origin in config("CORS_ALLOWED_ORIGINS", default="").split(",") if origin]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = config("GOOGLE_CLIENT_ID", default="")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = config("GOOGLE_CLIENT_SECRET", default="")
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["openid", "email", "profile"]
SOCIAL_AUTH_GOOGLE_OAUTH2_USE_UNIQUE_USER_ID = True

SOCIAL_AUTH_NAVER_KEY = config("NAVER_CLIENT_ID", default="")
SOCIAL_AUTH_NAVER_SECRET = config("NAVER_CLIENT_SECRET", default="")

SOCIAL_AUTH_KAKAO_KEY = config("KAKAO_CLIENT_ID", default="")
SOCIAL_AUTH_KAKAO_SECRET = config("KAKAO_CLIENT_SECRET", default="")
SOCIAL_AUTH_KAKAO_SCOPE = ["account_email", "profile_nickname", "profile_image"]

SOCIAL_AUTH_REQUESTS_TIMEOUT = config("SOCIAL_AUTH_REQUESTS_TIMEOUT", default=10, cast=int)
SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_LOGIN_ERROR_URL = "/login/"
SOCIAL_AUTH_USER_FIELDS = ["email"]
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "users.social_pipeline.ensure_email",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "users.social_pipeline.associate_active_user_by_email",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "users.social_pipeline.sync_tailtalk_social_data",
)

SOCIAL_AUTH_PROVIDERS = {
    "google": {
        "client_id": config("GOOGLE_CLIENT_ID", default=""),
        "client_secret": config("GOOGLE_CLIENT_SECRET", default=""),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
    },
    "naver": {
        "client_id": config("NAVER_CLIENT_ID", default=""),
        "client_secret": config("NAVER_CLIENT_SECRET", default=""),
        "authorize_url": "https://nid.naver.com/oauth2.0/authorize",
        "token_url": "https://nid.naver.com/oauth2.0/token",
        "userinfo_url": "https://openapi.naver.com/v1/nid/me",
    },
    "kakao": {
        "client_id": config("KAKAO_CLIENT_ID", default=""),
        "client_secret": config("KAKAO_CLIENT_SECRET", default=""),
        "authorize_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "userinfo_url": "https://kapi.kakao.com/v2/user/me",
    },
}

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
APP_BASE_URL = config("APP_BASE_URL", default="")
FASTAPI_INTERNAL_CHAT_URL = config("FASTAPI_INTERNAL_CHAT_URL", default="http://fastapi:8001/api/chat/")
_fastapi_recommend_url = config("FASTAPI_INTERNAL_RECOMMEND_URL", default="").strip()
if not _fastapi_recommend_url:
    _fastapi_chat_url = FASTAPI_INTERNAL_CHAT_URL.rstrip("/")
    if _fastapi_chat_url.endswith("/api/chat"):
        _fastapi_recommend_url = f"{_fastapi_chat_url.removesuffix('/api/chat')}/api/recommend/"
    else:
        _fastapi_recommend_url = "http://fastapi:8001/api/recommend/"
FASTAPI_INTERNAL_RECOMMEND_URL = _fastapi_recommend_url
INTERNAL_SERVICE_TOKEN = config("INTERNAL_SERVICE_TOKEN", default="dev-internal-token")
FASTAPI_STREAM_CONNECT_TIMEOUT = config("FASTAPI_STREAM_CONNECT_TIMEOUT", default=5, cast=float)
FASTAPI_STREAM_READ_TIMEOUT = config("FASTAPI_STREAM_READ_TIMEOUT", default=25, cast=float)
FASTAPI_STREAM_WRITE_TIMEOUT = config("FASTAPI_STREAM_WRITE_TIMEOUT", default=10, cast=float)
FASTAPI_STREAM_POOL_TIMEOUT = config("FASTAPI_STREAM_POOL_TIMEOUT", default=5, cast=float)
JUSO_CONFM_KEY = config(
    "JUSO_CONFIRM_KEY",
    default=config("JUSO_CONFM_KEY", default=config("JUSO_KEY", default="")),
)

AWS_S3_BUCKET_NAME = config("AWS_S3_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="")
AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default="")
AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default="")

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/chat/"
LOGOUT_REDIRECT_URL = "/login/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
