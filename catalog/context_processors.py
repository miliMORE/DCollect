from django.conf import settings as django_settings

from .models import SiteSettings, SurveyPeriod


def platform(request):
    settings_obj = None
    period = None
    my_case = None
    pending_clarifications = 0
    nav = ""
    try:
        settings_obj = SiteSettings.load()
        period = settings_obj.active_survey_period
        if period is None:
            period = SurveyPeriod.objects.filter(is_active=True).first()
    except Exception:
        settings_obj = None

    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and period and getattr(user, "role", None) == "county" and user.county_id:
        try:
            from collection.models import CountyCase, Clarification

            my_case = CountyCase.objects.filter(county=user.county, survey_period=period).first()
            if my_case:
                pending_clarifications = Clarification.objects.filter(case=my_case, resolved=False).count()
        except Exception:
            my_case = None

    path = getattr(request, "path", "") or ""
    if path.startswith("/accounts/login"):
        nav = "login"
    elif path.startswith("/accounts/audit"):
        nav = "audit"
    elif path.startswith("/accounts/manual"):
        nav = "manual"
    elif path.startswith("/accounts/data"):
        nav = "data"
    elif path.startswith("/accounts/users"):
        nav = "users"
    elif path.startswith("/accounts/password"):
        nav = "password"
    elif path.startswith("/setup/forms") or path.startswith("/setup/questions"):
        nav = "forms"
    elif path.startswith("/setup"):
        nav = "settings"
    elif path.startswith("/reports"):
        nav = "reports"
    elif path.startswith("/comparators"):
        nav = "comparators"
    elif path.startswith("/analysis"):
        nav = "analysis"
    elif path.startswith("/help"):
        nav = "help"
    elif path.startswith("/staff-survey"):
        nav = "staff"
    elif path.startswith("/questionnaires"):
        nav = "questionnaires"
    elif path.startswith("/cases"):
        nav = "cases"
    elif path in {"/", ""}:
        nav = "dashboard"

    idle = 0
    if user is not None and getattr(user, "is_authenticated", False):
        idle = int(getattr(django_settings, "SESSION_IDLE_TIMEOUT", 600) or 600)

    return {
        "site_settings": settings_obj,
        "active_period": period,
        "my_case": my_case,
        "pending_clarifications": pending_clarifications,
        "current_nav": nav,
        "idle_timeout_seconds": idle,
    }
