import os

from .settings import *  # noqa: F403
from .settings import DATABASES, required

DEBUG = False
REQUIRE_RESTRICTED_DB_ROLE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600

# The origin must be private and its reverse proxy must overwrite both headers.
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS") == "true"
if TRUST_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DATABASES["default"]["OPTIONS"] = {
    "sslmode": "verify-full",
    "sslrootcert": required("DB_SSL_ROOT_CERT"),
}
