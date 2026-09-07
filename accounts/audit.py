"""Platform audit trail. Visible only to administrators, not collection administrators."""

from django.http import HttpRequest
from django.urls import resolve, Resolver404
from django.utils import timezone

from .models import AuditEntry, User

SENSITIVE_KEYS = {
    "password",
    "passwd",
    "csrfmiddlewaretoken",
    "old_password",
    "new_password1",
    "new_password2",
    "password1",
    "password2",
    "secret_key",
    "token",
}

SAFE_VALUE_KEYS = {
    "username",
    "section",
    "status",
    "module",
    "first_name",
    "last_name",
    "role",
    "county",
    "name",
    "code",
    "measure",
    "job_title",
}

SKIP_PREFIXES = ("/static/", "/media/", "/health", "/favicon")

SKIP_URL_NAMES = {
    "accounts:login",
    "accounts:logout",
    "accounts:audit",
    "accounts:user_manual",
    "accounts:password_change",
    "accounts:user_new",
    "accounts:user_edit",
    "accounts:user_toggle",
    "accounts:user_delete",
    "accounts:create_county_users",
    "accounts:data",
    "collection:comparator_delete",
    "accounts:purge_county",
    "accounts:purge_user_data",
    "accounts:reset_data",
    "health",
}

DOWNLOAD_URL_NAMES = {
    "reports:county_pack",
    "reports:county_complete",
    "reports:progress",
    "reports:questionnaire_extract",
    "reports:analysis_workbook",
    "reports:individuals_extract",
    "accounts:audit_export",
    "accounts:user_manual",
    "reports:job_groups",
    "reports:benefits",
    "reports:documents",
    "reports:county_individuals",
    "collection:document_download",
    "collection:document_file_download",
    "collection:documents_zip",
}

URL_ACTIONS = {
    "accounts:password_change": ("auth", "Changed own password"),
    "accounts:user_new": ("users", "Created a user account"),
    "accounts:user_edit": ("users", "Updated a user account"),
    "accounts:user_toggle": ("users", "Changed a user account status"),
    "accounts:user_delete": ("users", "Deleted a user account"),
    "accounts:create_county_users": ("users", "Created missing county logins"),
    "accounts:purge_county": ("collection", "Deleted collected data for a county"),
    "accounts:purge_user_data": ("collection", "Deleted data collected by a user"),
    "accounts:reset_data": ("collection", "Reset all collected survey data"),
    "accounts:audit_export": ("audit", "Downloaded the audit trail"),
    "accounts:user_manual": ("audit", "Downloaded the user manual"),
    "catalog:settings": ("settings", "Updated platform or collection settings"),
    "catalog:forms": ("settings", "Updated form completion rules"),
    "catalog:question_new": ("settings", "Added a questionnaire question"),
    "catalog:question_edit": ("settings", "Updated a questionnaire question"),
    "catalog:question_delete": ("settings", "Removed a questionnaire question"),
    "catalog:period_new": ("settings", "Created a survey period"),
    "catalog:period_edit": ("settings", "Updated a survey period"),
    "catalog:period_activate": ("settings", "Activated a survey period"),
    "catalog:option_new": ("settings", "Created a dropdown list"),
    "catalog:option_edit": ("settings", "Updated a dropdown list"),
    "catalog:catalog_new": ("settings", "Added a catalogue record"),
    "catalog:catalog_edit": ("settings", "Updated a catalogue record"),
    "collection:open_period": ("collection", "Opened county files for the active period"),
    "collection:case_hub": ("collection", "Updated county file assignment or notes"),
    "collection:questionnaire": ("collection", "Saved questionnaire answers"),
    "collection:jobs": ("collection", "Saved benchmark positions"),
    "collection:benefits": ("collection", "Saved the benefits matrix"),
    "collection:documents": ("collection", "Updated a supporting document"),
    "collection:validation": ("collection", "Updated the validation checklist"),
    "collection:certify": ("collection", "Certified a county file"),
    "collection:submit": ("collection", "Submitted a county file for review"),
    "collection:reopen": ("collection", "Returned a county file for clarification"),
    "collection:validate": ("collection", "Marked a county file as validated"),
    "collection:clarifications": ("collection", "Requested a clarification"),
    "collection:resolve": ("collection", "Answered a clarification"),
    "collection:comparator_edit": ("comparators", "Updated a comparator organisation"),
    "collection:comparator_delete": ("comparators", "Deleted a comparator organisation"),
    "collection:comparator_pay": ("comparators", "Saved comparator pay"),
    "collection:comparator_benefits": ("comparators", "Saved comparator benefits"),
    "collection:public_survey": ("staff", "Submitted a staff survey response"),
    "reports:county_pack": ("reports", "Downloaded a county pack"),
    "reports:county_complete": ("reports", "Downloaded a complete county file"),
    "reports:progress": ("reports", "Downloaded the collection progress report"),
    "reports:questionnaire_extract": ("reports", "Downloaded the questionnaire extract"),
    "reports:analysis_workbook": ("reports", "Downloaded the market position workbook"),
    "reports:individuals_extract": ("reports", "Downloaded individual responses"),
    "reports:job_groups": ("reports", "Downloaded the job group pay extract"),
    "reports:benefits": ("reports", "Downloaded the benefits extract"),
    "reports:documents": ("reports", "Downloaded the document register"),
    "reports:county_individuals": ("reports", "Downloaded a county's individual responses"),
    "collection:document_download": ("reports", "Downloaded a county document"),
    "collection:document_file_download": ("reports", "Downloaded a county document"),
    "collection:document_file_delete": ("collection", "Removed a supporting document file"),
    "collection:documents_zip": ("reports", "Downloaded a county document zip"),
}


def client_ip(request):
    if request is None:
        return None
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR") or None


def _actor_fields(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return {
            "actor": None,
            "actor_username": "",
            "actor_name": "Unauthenticated",
            "actor_role": "",
        }
    name = user.get_full_name().strip() if hasattr(user, "get_full_name") else ""
    return {
        "actor": user if getattr(user, "pk", None) else None,
        "actor_username": getattr(user, "username", "") or "",
        "actor_name": name or getattr(user, "username", "") or "",
        "actor_role": getattr(user, "role", "") or "",
    }


def record_event(
    *,
    action,
    summary,
    request=None,
    user=None,
    category=AuditEntry.Category.OTHER,
    detail="",
    outcome=AuditEntry.Outcome.SUCCESS,
    county=None,
    case=None,
    target_label="",
    status_code=None,
    actor_username="",
):
    try:
        if request is not None and user is None:
            user = getattr(request, "user", None)
        fields = _actor_fields(user)
        if actor_username:
            fields["actor_username"] = actor_username[:150]
            if not fields["actor_name"] or fields["actor_name"] == "Unauthenticated":
                fields["actor_name"] = actor_username[:200]
        if case is not None and county is None:
            county = getattr(case, "county", None)
        if case is not None and not target_label:
            target_label = str(case)
        agent = ""
        path = ""
        method = ""
        ip = None
        if request is not None:
            ip = client_ip(request)
            agent = (request.META.get("HTTP_USER_AGENT") or "")[:255]
            path = (request.get_full_path() or "")[:255]
            method = request.method
        AuditEntry.objects.create(
            action=action[:80],
            summary=summary[:255],
            category=category,
            detail=detail or "",
            outcome=outcome,
            county=county,
            case=case,
            target_label=(target_label or "")[:255],
            ip_address=ip,
            user_agent=agent,
            path=path,
            method=method,
            status_code=status_code,
            **fields,
        )
    except Exception:
        return None


def _resolve(request):
    try:
        return resolve(request.path)
    except Resolver404:
        return None


def _should_record(request, response):
    path = request.path or ""
    if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
        return False
    match = _resolve(request)
    url_name = ""
    if match is not None:
        url_name = f"{match.namespace}:{match.url_name}" if match.namespace else (match.url_name or "")
    if url_name in SKIP_URL_NAMES:
        return False
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    if url_name in DOWNLOAD_URL_NAMES and request.method == "GET" and getattr(response, "status_code", 0) < 400:
        return True
    if path.startswith("/admin/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    return False


def _case_from_request(request, match):
    if match is None:
        return None, None
    pk = match.kwargs.get("pk") or match.kwargs.get("case")
    if not pk:
        return None, None
    try:
        from collection.models import CountyCase

        case = CountyCase.objects.select_related("county").filter(pk=pk).first()
        if case:
            return case, case.county
    except Exception:
        return None, None
    return None, None


def _posted_detail(request):
    bits = []
    section = request.GET.get("section") or request.POST.get("section")
    if section:
        bits.append(f"Questionnaire section {section.upper()}")
    keys = []
    values = []
    for key in request.POST.keys():
        low = key.lower()
        if low in SENSITIVE_KEYS or low.endswith("password"):
            continue
        keys.append(key)
        if key in SAFE_VALUE_KEYS:
            raw = request.POST.get(key)
            if raw not in (None, ""):
                values.append(f"{key}={raw}")
    if values:
        bits.append("Values: " + ", ".join(values[:12]))
    if request.FILES:
        names = [upload.name for upload in request.FILES.values() if getattr(upload, "name", "")]
        if names:
            bits.append("Files: " + ", ".join(names[:8]))
    if keys and not values:
        unique = sorted({k.split("-")[0] for k in keys if k != "stay"})[:16]
        if unique:
            bits.append("Fields submitted: " + ", ".join(unique))
    return " · ".join(bits)


def record_request(request: HttpRequest, response):
    if not _should_record(request, response):
        return
    match = _resolve(request)
    url_name = ""
    if match is not None:
        url_name = f"{match.namespace}:{match.url_name}" if match.namespace else (match.url_name or "")
    category, summary = URL_ACTIONS.get(url_name, (AuditEntry.Category.OTHER, ""))
    if not summary:
        if (request.path or "").startswith("/admin/"):
            category, summary = AuditEntry.Category.ADMIN, "Changed a record in Django admin"
        else:
            summary = f"Submitted {request.path}"
    if url_name == "catalog:catalog_edit" or url_name == "catalog:catalog_new":
        key = (match.kwargs.get("key") if match else "") or ""
        if key:
            summary = f"{summary} ({key})"
    case, county = _case_from_request(request, match)
    if case and "county file" not in summary.lower() and case.county:
        summary = f"{summary} — {case.county.name}"
    status = getattr(response, "status_code", None)
    outcome = AuditEntry.Outcome.SUCCESS
    if status and int(status) >= 400:
        outcome = AuditEntry.Outcome.FAILURE
        summary = f"{summary} (not completed)"
    detail_parts = [_posted_detail(request)]
    if status:
        detail_parts.append(f"HTTP {status}")
    when = timezone.localtime()
    detail_parts.append(f"Recorded {when.strftime('%d %b %Y, %H:%M:%S %Z')}")
    target = ""
    if case:
        target = str(case)
    elif match and match.kwargs:
        target = ", ".join(f"{k}={v}" for k, v in match.kwargs.items())
    record_event(
        action=url_name or request.path[:80],
        summary=summary,
        request=request,
        category=category,
        detail=" · ".join(p for p in detail_parts if p),
        outcome=outcome,
        county=county,
        case=case,
        target_label=target,
        status_code=status,
    )
