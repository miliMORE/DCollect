from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from .models import CountyCase


def role_required(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in roles or (
                "admin" in roles and request.user.is_admin_role
            ):
                return view(request, *args, **kwargs)
            return HttpResponseForbidden("You do not have access to this page.")

        return _wrapped

    return decorator


admin_required = role_required("admin")
setup_required = role_required("admin", "collection_admin")
reviewer_required = role_required("admin", "collection_admin", "consultant")
analyst_required = role_required("admin", "collection_admin", "consultant", "analyst")


def can_view_analysis(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_analyst_role:
        return True
    if user.role == user.Role.COUNTY:
        from catalog.models import SiteSettings

        return bool(SiteSettings.load().allow_county_see_analysis)
    return False


def analysis_required(view):
    @login_required
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if can_view_analysis(request.user):
            return view(request, *args, **kwargs)
        return HttpResponseForbidden("You do not have access to this page.")

    return _wrapped


def get_visible_cases(user, period=None):
    qs = CountyCase.objects.select_related("county", "survey_period", "assigned_consultant")
    if period:
        qs = qs.filter(survey_period=period)
    if user.can_configure or user.role == user.Role.ANALYST:
        return qs
    if user.role == user.Role.CONSULTANT:
        assigned = qs.filter(assigned_consultant=user)
        if assigned.exists():
            return assigned
        return qs
    if user.role == user.Role.COUNTY and user.county_id:
        return qs.filter(county=user.county)
    return qs.none()


def get_accessible_case(user, pk):
    case = get_object_or_404(
        CountyCase.objects.select_related("county", "survey_period", "assigned_consultant"),
        pk=pk,
    )
    if user.can_configure or user.role in {user.Role.ANALYST, user.Role.CONSULTANT}:
        if user.role == user.Role.CONSULTANT and case.assigned_consultant_id not in {None, user.id}:
            others = CountyCase.objects.filter(
                survey_period=case.survey_period, assigned_consultant=user
            )
            if others.exists() and case.assigned_consultant_id != user.id:
                raise PermissionError
        return case
    if user.role == user.Role.COUNTY and user.county_id == case.county_id:
        return case
    raise PermissionError


def case_required(view):
    @login_required
    @wraps(view)
    def _wrapped(request, pk, *args, **kwargs):
        try:
            case = get_accessible_case(request.user, pk)
        except PermissionError:
            return HttpResponseForbidden("You cannot open this county file.")
        return view(request, case, *args, **kwargs)

    return _wrapped
