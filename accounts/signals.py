from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .audit import record_event
from .models import AuditEntry


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    extra = []
    if getattr(user, "role", None):
        extra.append(user.get_role_display())
    if getattr(user, "county", None):
        extra.append(user.county.name)
    if request is not None and hasattr(request, "session"):
        from django.utils import timezone

        request.session["_last_activity"] = timezone.now().timestamp()
    record_event(
        action="accounts:login",
        summary="Signed in",
        request=request,
        user=user,
        category=AuditEntry.Category.AUTH,
        detail=" · ".join(extra),
        county=getattr(user, "county", None),
        outcome=AuditEntry.Outcome.SUCCESS,
        status_code=200,
    )


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    idle = bool(request and getattr(request, "_logout_reason", "") == "inactivity")
    minutes = 10
    try:
        from django.conf import settings

        minutes = max(1, int(getattr(settings, "SESSION_IDLE_TIMEOUT", 600) or 600) // 60)
    except Exception:
        pass
    record_event(
        action="accounts:timeout" if idle else "accounts:logout",
        summary=f"Signed out after {minutes} minutes of inactivity" if idle else "Signed out",
        request=request,
        user=user,
        category=AuditEntry.Category.AUTH,
        detail="Session closed because there was no activity." if idle else "",
        outcome=AuditEntry.Outcome.SUCCESS,
        county=getattr(user, "county", None) if user else None,
        status_code=200,
    )


@receiver(user_login_failed)
def audit_login_failed(sender, credentials, request, **kwargs):
    username = (credentials or {}).get("username") or "unknown"
    record_event(
        action="accounts:login_failed",
        summary="Failed sign-in attempt",
        request=request,
        user=None,
        category=AuditEntry.Category.AUTH,
        detail=f"Username entered: {username}",
        outcome=AuditEntry.Outcome.FAILURE,
        status_code=401,
        target_label=username,
        actor_username=username,
    )
