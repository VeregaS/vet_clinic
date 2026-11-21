from ipaddress import ip_address
from time import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse
from django.utils.crypto import salted_hmac

from .models import RequestBudget

POST_SCOPES = {"login": "login", "admin:login": "login", "home": "booking"}
CONTENT_POLICY = (
    "default-src 'self'; base-uri 'self'; object-src 'none'; "
    "frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "font-src 'self' https://cdn.jsdelivr.net"
)


def client_address(request):
    addresses = []
    if settings.TRUST_PROXY_HEADERS:
        addresses.append(request.META.get("HTTP_X_REAL_IP", ""))
    addresses.append(request.META.get("REMOTE_ADDR", ""))
    for candidate in addresses:
        try:
            return str(ip_address(candidate))
        except ValueError:
            continue
    return "unknown"


def consume_budget(scope, address, now, limit, period):
    window = now - now % period
    key = salted_hmac("clinic.request-budget", f"{scope}:{address}", algorithm="sha256")

    # PostgreSQL applies the increment and the limit in one statement.
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO clinic_requestbudget (client_key, window_start, attempts)
            VALUES (%s, %s, 1)
            ON CONFLICT (client_key, window_start)
            DO UPDATE SET attempts = clinic_requestbudget.attempts + 1
            WHERE clinic_requestbudget.attempts < %s
            RETURNING attempts
            """,
            [key.hexdigest(), window, limit],
        )
        allowed = cursor.fetchone() is not None
    if cache.add("clinic:purge-request-budgets", True, timeout=300):
        RequestBudget.objects.filter(window_start__lt=now - 86400).delete()
    return 0 if allowed else window + period - now


class RequestSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CONTENT_POLICY)
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != "POST":
            return None
        scope = POST_SCOPES.get(request.resolver_match.view_name)
        if scope is None:
            return None
        limit, period = settings.SECURITY_POST_LIMITS[scope]
        retry = consume_budget(
            scope, client_address(request), int(time()), limit, period
        )
        if retry:
            return HttpResponse(
                "Слишком много попыток. Попробуйте позже.",
                status=429,
                headers={"Retry-After": str(retry), "Cache-Control": "no-store"},
            )
        return None
