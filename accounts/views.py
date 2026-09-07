import csv
from datetime import datetime, time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from catalog.models import County
from collection.permissions import setup_required

from .audit import record_event
from .data import (
    describe_user_changes,
    format_purge_summary,
    purge_county_data,
    purge_user_collected_data,
    reset_collected_data,
)
from .forms import PlatformUserForm, StyledAuthenticationForm, StyledPasswordChangeForm
from .models import AuditEntry, User


class PlatformLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


class PlatformLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if request.POST.get("reason") == "inactivity":
            request._logout_reason = "inactivity"
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        if getattr(self.request, "_logout_reason", "") == "inactivity":
            return f"{reverse('accounts:login')}?timeout=1"
        return super().get_success_url()

    def post(self, request, *args, **kwargs):
        idle = getattr(request, "_logout_reason", "") == "inactivity"
        response = super().post(request, *args, **kwargs)
        if idle:
            messages.warning(
                request,
                "You were signed out after 10 minutes of inactivity. Sign in again.",
            )
        return response


@login_required
def password_change(request):
    form = StyledPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=["must_change_password"])
        update_session_auth_hash(request, user)
        record_event(
            action="accounts:password_change",
            summary="Changed own password",
            request=request,
            user=request.user,
            category=AuditEntry.Category.AUTH,
            detail="The new password was not stored in the audit trail.",
            county=getattr(request.user, "county", None),
        )
        messages.success(request, "Password updated.")
        return redirect("collection:dashboard")
    return render(
        request,
        "accounts/password_change.html",
        {"form": form, "forced": request.user.must_change_password},
    )


@setup_required
def user_list(request):
    users = User.objects.select_related("county")
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()
    if role:
        users = users.filter(role=role)
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(county__name__icontains=q)
        )
    counts = {
        "total": User.objects.count(),
        "admin": User.objects.filter(role=User.Role.ADMIN, is_active=True).count(),
        "collection_admin": User.objects.filter(
            role=User.Role.COLLECTION_ADMIN, is_active=True
        ).count(),
        "consultant": User.objects.filter(role=User.Role.CONSULTANT, is_active=True).count(),
        "analyst": User.objects.filter(role=User.Role.ANALYST, is_active=True).count(),
        "county": User.objects.filter(role=User.Role.COUNTY, is_active=True).count(),
    }
    covered = set(
        User.objects.filter(role=User.Role.COUNTY, is_active=True, county__isnull=False).values_list(
            "county_id", flat=True
        )
    )
    missing_counties = County.objects.filter(is_active=True).exclude(pk__in=covered).count()
    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
            "setup_section": "users",
            "role": role,
            "status": status,
            "q": q,
            "counts": counts,
            "missing_counties": missing_counties,
            "roles": User.Role.choices,
        },
    )


@setup_required
def user_edit(request, pk=None):
    instance = get_object_or_404(User, pk=pk) if pk else None
    if instance and instance.role == User.Role.ADMIN and not request.user.can_edit_site:
        return HttpResponseForbidden("You cannot edit a platform administrator account.")
    form = PlatformUserForm(request.POST or None, instance=instance, request_user=request.user)
    if request.method == "POST" and form.is_valid():
        if instance and instance.pk == request.user.pk:
            new_role = form.cleaned_data.get("role")
            if new_role != instance.role and not request.user.is_superuser:
                form.add_error("role", "You cannot change your own role.")
            elif form.cleaned_data.get("is_active") is False:
                form.add_error("is_active", "You cannot deactivate your own account.")
        if not form.errors:
            created = instance is None
            detail = describe_user_changes(instance, form)
            saved = form.save()
            record_event(
                action="accounts:user_new" if created else "accounts:user_edit",
                summary="Created a user account" if created else "Updated a user account",
                request=request,
                category=AuditEntry.Category.USERS,
                detail=detail,
                county=saved.county,
                target_label=saved.username,
            )
            messages.success(request, "User saved.")
            return redirect("accounts:users")
    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "instance": instance, "setup_section": "users"},
    )


@setup_required
@require_POST
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:users")
    if user.role == User.Role.ADMIN and not request.user.can_edit_site:
        messages.error(request, "You cannot change a platform administrator account.")
        return redirect("accounts:users")
    if user.role == User.Role.ADMIN and user.is_active:
        remaining = User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=user.pk).count()
        if remaining == 0:
            messages.error(request, "Keep at least one active administrator.")
            return redirect("accounts:users")
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    state = "active" if user.is_active else "inactive"
    record_event(
        action="accounts:user_toggle",
        summary="Reactivated a user account" if user.is_active else "Deactivated a user account",
        request=request,
        category=AuditEntry.Category.USERS,
        detail=f"{user.username} ({user.get_role_display()}) is now {state}. Collected survey data was left in place.",
        county=user.county,
        target_label=user.username,
    )
    messages.success(request, f"{user.username} is now {state}.")
    return redirect("accounts:users")


@setup_required
@require_POST
def create_missing_county_users(request):
    password = getattr(settings, "BOOTSTRAP_PASSWORD", "ChangeMe!2026")
    created = []
    covered = set(
        User.objects.filter(
            role=User.Role.COUNTY, is_active=True, county__isnull=False
        ).values_list("county_id", flat=True)
    )
    for county in County.objects.filter(is_active=True).exclude(pk__in=covered):
        base = f"county.{slugify(county.name).replace('-', '')[:24]}"
        username = base
        suffix = 2
        while User.objects.filter(username=username).exists():
            username = f"{base}{suffix}"
            suffix += 1
        user = User(
            username=username,
            role=User.Role.COUNTY,
            county=county,
            first_name=county.name,
            last_name="Respondent",
            email=f"{username}@dcollect.local",
            must_change_password=True,
            is_active=True,
        )
        user.set_password(password)
        user.save()
        created.append(username)
    if created:
        record_event(
            action="accounts:create_county_users",
            summary=f"Created {len(created)} county login(s)",
            request=request,
            category=AuditEntry.Category.USERS,
            detail="Accounts: " + ", ".join(created),
        )
        messages.success(
            request,
            f"Created {len(created)} county login(s): {', '.join(created)}. "
            f"Initial password is the bootstrap password. They must change it at first sign-in.",
        )
    else:
        messages.info(request, "Every active county already has a respondent account.")
    return redirect("accounts:users")


@login_required
@require_POST
def user_delete(request, pk):
    _admin_only(request)
    user = get_object_or_404(User, pk=pk)
    confirm = (request.POST.get("confirm") or "").strip()
    if user.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("accounts:users")
    if user.role == User.Role.ADMIN:
        remaining = User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=user.pk).count()
        if remaining == 0:
            messages.error(request, "Keep at least one administrator.")
            return redirect("accounts:users")
    if confirm != user.username:
        messages.error(request, "Type the username exactly to confirm deletion.")
        return redirect("accounts:user_edit", pk=user.pk)
    label = f"{user.get_full_name() or user.username} ({user.get_role_display()})"
    username = user.username
    county = user.county
    user.delete()
    record_event(
        action="accounts:user_delete",
        summary=f"Deleted user account {username}",
        request=request,
        category=AuditEntry.Category.USERS,
        detail=(
            f"Removed the login for {label}. County files, answers and uploads were left in place. "
            "Earlier audit entries for this person remain, under their username."
        ),
        county=county,
        target_label=username,
    )
    messages.success(
        request,
        f"{username} was deleted. Their collected survey data and audit history were kept.",
    )
    return redirect("accounts:users")


def _admin_only(request):
    if not request.user.is_authenticated or not request.user.can_see_audit:
        raise PermissionDenied("The audit trail is available only to platform administrators.")
    return None


def _audit_queryset(request):
    entries = AuditEntry.objects.select_related("actor", "county", "case", "case__county", "case__survey_period")
    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip()
    category = (request.GET.get("category") or "").strip()
    outcome = (request.GET.get("outcome") or "").strip()
    county_id = (request.GET.get("county") or "").strip()
    date_from = (request.GET.get("from") or "").strip()
    date_to = (request.GET.get("to") or "").strip()
    if q:
        entries = entries.filter(
            Q(summary__icontains=q)
            | Q(detail__icontains=q)
            | Q(actor_username__icontains=q)
            | Q(actor_name__icontains=q)
            | Q(target_label__icontains=q)
            | Q(path__icontains=q)
            | Q(ip_address__icontains=q)
        )
    if role:
        entries = entries.filter(actor_role=role)
    if category:
        entries = entries.filter(category=category)
    if outcome:
        entries = entries.filter(outcome=outcome)
    if county_id.isdigit():
        entries = entries.filter(county_id=int(county_id))
    tz = timezone.get_current_timezone()
    if date_from:
        try:
            start = datetime.strptime(date_from, "%Y-%m-%d")
            entries = entries.filter(
                created_at__gte=timezone.make_aware(datetime.combine(start.date(), time.min), tz)
            )
        except ValueError:
            pass
    if date_to:
        try:
            end = datetime.strptime(date_to, "%Y-%m-%d")
            entries = entries.filter(
                created_at__lte=timezone.make_aware(datetime.combine(end.date(), time.max), tz)
            )
        except ValueError:
            pass
    return entries


def _audit_filters(request):
    return {
        "q": request.GET.get("q", "").strip(),
        "role": request.GET.get("role", "").strip(),
        "category": request.GET.get("category", "").strip(),
        "outcome": request.GET.get("outcome", "").strip(),
        "county_id": request.GET.get("county", "").strip(),
        "date_from": request.GET.get("from", "").strip(),
        "date_to": request.GET.get("to", "").strip(),
        "roles": User.Role.choices,
        "categories": AuditEntry.Category.choices,
        "counties": County.objects.filter(is_active=True).order_by("name"),
    }


@login_required
def user_manual(request):
    _admin_only(request)
    path = Path(settings.BASE_DIR) / "docs" / "DCollect-User-Manual.pdf"
    if not path.is_file():
        messages.error(request, "The user manual PDF is not on this server.")
        return redirect("collection:dashboard")
    record_event(
        action="accounts:user_manual",
        summary="Downloaded the user manual",
        request=request,
        category=AuditEntry.Category.AUDIT,
        detail="DCollect-User-Manual.pdf",
    )
    handle = path.open("rb")
    return FileResponse(handle, as_attachment=True, filename="DCollect-User-Manual.pdf")


@login_required
def audit_trail(request):
    _admin_only(request)
    entries = _audit_queryset(request)
    paginator = Paginator(entries, 50)
    page = paginator.get_page(request.GET.get("page") or 1)
    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "accounts/audit.html",
        {
            "page": page,
            "total": paginator.count,
            "querystring": query.urlencode(),
            **_audit_filters(request),
        },
    )


@login_required
def audit_export(request):
    _admin_only(request)
    entries = _audit_queryset(request)
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="DCollect-audit-trail-{stamp}.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "When",
            "User",
            "Username",
            "Role",
            "Action",
            "Category",
            "County / file",
            "Outcome",
            "IP address",
            "Detail",
            "Page",
        ]
    )
    for row in entries.iterator():
        writer.writerow(
            [
                timezone.localtime(row.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                row.actor_name,
                row.actor_username,
                row.actor_role_label(),
                row.summary,
                row.get_category_display(),
                row.target_label or (row.county.name if row.county_id else ""),
                row.get_outcome_display(),
                row.ip_address or "",
                row.detail,
                row.path,
            ]
        )
    return response


@login_required
def data_admin(request):
    _admin_only(request)
    from collection.models import CountyCase, IndividualResponse

    counties = County.objects.filter(is_active=True).order_by("name")
    users = User.objects.select_related("county").order_by("username")
    return render(
        request,
        "accounts/data_admin.html",
        {
            "setup_section": "data",
            "counties": counties,
            "users": users,
            "file_count": CountyCase.objects.count(),
            "staff_count": IndividualResponse.objects.count(),
            "user_count": User.objects.count(),
        },
    )


@login_required
@require_POST
def purge_county(request):
    _admin_only(request)
    county = get_object_or_404(County, pk=request.POST.get("county_id"))
    confirm = (request.POST.get("confirm") or "").strip()
    if confirm.casefold() != county.name.casefold():
        messages.error(request, f'Type “{county.name}” exactly to confirm.')
        return redirect("accounts:data")
    with transaction.atomic():
        stats = purge_county_data(county)
    summary = format_purge_summary(stats)
    record_event(
        action="accounts:purge_county",
        summary=f"Deleted collected data for {county.name}",
        request=request,
        category=AuditEntry.Category.COLLECTION,
        detail=(
            f"Removed {summary}. Catalogues, user logins and the audit trail were kept. "
            "A new county file can be opened from Variables & settings."
        ),
        county=county,
        target_label=county.name,
    )
    messages.success(request, f"Collected data for {county.name} has been removed ({summary}).")
    return redirect("accounts:data")


@login_required
@require_POST
def purge_user_data(request):
    _admin_only(request)
    user = get_object_or_404(User, pk=request.POST.get("user_id"))
    confirm = (request.POST.get("confirm") or "").strip()
    if confirm != user.username:
        messages.error(request, f'Type “{user.username}” exactly to confirm.')
        return redirect("accounts:data")
    with transaction.atomic():
        stats = purge_user_collected_data(user)
    summary = format_purge_summary(stats)
    record_event(
        action="accounts:purge_user_data",
        summary=f"Deleted data collected by {user.username}",
        request=request,
        category=AuditEntry.Category.COLLECTION,
        detail=(
            f"Removed {summary}. The login {user.username} was not deleted. "
            "Audit history for this person remains."
        ),
        county=user.county,
        target_label=user.username,
    )
    messages.success(
        request,
        f"Collected data for {user.username} has been removed ({summary}). The login remains.",
    )
    return redirect("accounts:data")


@login_required
@require_POST
def reset_data(request):
    _admin_only(request)
    confirm = (request.POST.get("confirm") or "").strip()
    if confirm != "RESET ALL COLLECTED DATA":
        messages.error(request, "Type RESET ALL COLLECTED DATA in capital letters to confirm.")
        return redirect("accounts:data")
    with transaction.atomic():
        stats = reset_collected_data()
    summary = format_purge_summary(stats)
    record_event(
        action="accounts:reset_data",
        summary="Reset all collected survey data",
        request=request,
        category=AuditEntry.Category.COLLECTION,
        detail=(
            f"The survey is empty of answers again ({summary}). "
            "Catalogues, users, passwords and this audit trail were not reset. "
            "Open county files again when you are ready to collect."
        ),
        target_label="All counties",
    )
    messages.success(
        request,
        "All collected survey data has been cleared. Users and catalogues are unchanged.",
    )
    return redirect("accounts:data")


