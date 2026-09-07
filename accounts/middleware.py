from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode

from .audit import record_request


class IdleTimeoutMiddleware:
    """Sign out after SESSION_IDLE_TIMEOUT seconds without a request."""

    exempt_prefixes = (
        "/static/",
        "/media/",
        "/health",
        "/accounts/login",
        "/accounts/logout",
        "/s/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if any(path.startswith(prefix) for prefix in self.exempt_prefixes):
            return self.get_response(request)
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        timeout = int(getattr(settings, "SESSION_IDLE_TIMEOUT", 600) or 600)
        now = timezone.now().timestamp()
        last = request.session.get("_last_activity")
        try:
            last = float(last) if last is not None else None
        except (TypeError, ValueError):
            last = None
        if last is not None and (now - last) > timeout:
            request._logout_reason = "inactivity"
            logout(request)
            minutes = max(1, timeout // 60)
            messages.warning(
                request,
                f"You were signed out after {minutes} minutes of inactivity. Sign in again.",
                fail_silently=True,
            )
            login_url = reverse("accounts:login")
            query = urlencode({"timeout": "1", "next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")
        request.session["_last_activity"] = now
        return self.get_response(request)


class PasswordChangeMiddleware:

    exempt_names = {
        "accounts:password_change",
        "accounts:logout",
        "accounts:login",
        "health",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and getattr(user, "must_change_password", False):
            path = request.path
            if not (
                path.startswith("/accounts/password")
                or path.startswith("/accounts/logout")
                or path.startswith("/admin/")
                or path.startswith("/health")
            ):
                return redirect("accounts:password_change")
        return self.get_response(request)


class AuditTrailMiddleware:
    """Records signed-in actions for the administrator audit trail."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            record_request(request, response)
        except Exception:
            pass
        return response
