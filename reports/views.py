from urllib.parse import quote

import logging

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)
from django.utils import timezone
from django.utils.text import slugify

from catalog.models import ComparatorOrganization, SiteSettings, SurveyPeriod
from collection.models import log_event
from collection.permissions import analyst_required, can_view_analysis, case_required, get_visible_cases
from collection.services import ensure_case_structure

from .excel import (
    build_analysis_workbook,
    build_benefits_extract,
    build_county_complete_zip,
    build_county_pack,
    build_documents_register,
    build_individuals_extract,
    build_job_group_extract,
    build_progress_workbook,
    build_questionnaire_extract,
)


def _period():
    settings_obj = SiteSettings.load()
    return settings_obj.active_survey_period or SurveyPeriod.objects.filter(is_active=True).first()


def _zip(content, filename):
    safe = slugify(filename.replace(".zip", ""), allow_unicode=False) or "dcollect-complete"
    download_name = f"{safe}.zip"
    response = HttpResponse(content, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{download_name}"; filename*=UTF-8\'\'{quote(download_name)}'
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _xlsx(content, filename):
    safe = slugify(filename.replace(".xlsx", ""), allow_unicode=False) or "dcollect-report"
    download_name = f"{safe}.xlsx"
    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{download_name}"; filename*=UTF-8\'\'{quote(download_name)}'
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _report_cases(user, period):
    return (
        get_visible_cases(user, period)
        .select_related("county", "survey_period", "assigned_consultant")
        .prefetch_related(
            "job_rows__job_group",
            "benefit_rows__benefit",
            "documents__document_type",
            "documents__attachments",
            "questionnaire",
        )
        .order_by("county__name")
    )


@analyst_required
def centre(request):
    period = _period()
    cases = _report_cases(request.user, period)
    return render(
        request,
        "reports/centre.html",
        {
            "period": period,
            "cases": cases,
            "case_count": cases.count(),
        },
    )


@case_required
def county_pack(request, case):
    try:
        ensure_case_structure(case)
        stamp = timezone.now().strftime("%Y%m%d")
        name = f"DCollect {case.county.name} {case.survey_period.code} {stamp}"
        log_event(case, request.user, "county pack downloaded")
        return _xlsx(build_county_pack(case, include_market=can_view_analysis(request.user)), name)
    except Exception:
        logger.exception("County pack failed for case %s", case.pk)
        messages.error(request, f"Could not build the county pack for {case.county.name}.")
        if request.user.is_analyst_role:
            return redirect("reports:centre")
        return redirect("collection:case_hub", pk=case.pk)


@case_required
def county_complete(request, case):
    try:
        ensure_case_structure(case)
        stamp = timezone.now().strftime("%Y%m%d")
        name = f"DCollect {case.county.name} complete {case.survey_period.code} {stamp}"
        log_event(case, request.user, "complete county file downloaded")
        return _zip(
            build_county_complete_zip(case, include_market=can_view_analysis(request.user)),
            name,
        )
    except Exception:
        logger.exception("Complete county zip failed for case %s", case.pk)
        messages.error(request, f"Could not build the complete file for {case.county.name}.")
        if request.user.is_analyst_role:
            return redirect("reports:centre")
        return redirect("collection:case_hub", pk=case.pk)


@analyst_required
def progress_report(request):
    period = _period()
    cases = _report_cases(request.user, period)
    stamp = timezone.now().strftime("%Y%m%d")
    code = period.code if period else "period"
    return _xlsx(build_progress_workbook(cases), f"DCollect progress {code} {stamp}")


@analyst_required
def questionnaire_extract(request):
    period = _period()
    cases = _report_cases(request.user, period)
    stamp = timezone.now().strftime("%Y%m%d")
    code = period.code if period else "period"
    return _xlsx(build_questionnaire_extract(cases), f"DCollect questionnaire extract {code} {stamp}")


@analyst_required
def individuals_extract(request):
    period = _period()
    cases = _report_cases(request.user, period)
    county_ids = list(cases.values_list("county_id", flat=True))
    stamp = timezone.now().strftime("%Y%m%d")
    code = period.code if period else "period"
    return _xlsx(
        build_individuals_extract(period, county_ids=county_ids),
        f"DCollect individual responses {code} {stamp}",
    )


@case_required
def county_individuals(request, case):
    stamp = timezone.now().strftime("%Y%m%d")
    name = f"DCollect {case.county.name} individual responses {case.survey_period.code} {stamp}"
    log_event(case, request.user, "individual responses downloaded")
    return _xlsx(
        build_individuals_extract(case.survey_period, county_ids=[case.county_id]),
        name,
    )


@analyst_required
def analysis_workbook(request):
    period = _period()
    cases = _report_cases(request.user, period)
    orgs = ComparatorOrganization.objects.filter(is_active=True, include_in_market_median=True)
    stamp = timezone.now().strftime("%Y%m%d")
    code = period.code if period else "period"
    return _xlsx(build_analysis_workbook(cases, orgs, period), f"DCollect market position {code} {stamp}")


@analyst_required
def job_group_extract(request):
    period = _period()
    cases = _report_cases(request.user, period)
    stamp = timezone.now().strftime("%Y%m%d")
    code = period.code if period else "period"
    return _xlsx(build_job_group_extract(cases), f"DCollect job group pay {code} {stamp}")


@analyst_required
def benefits_extract(request):
    period = _period()
    cases = _report_cases(request.user, period)
    stamp = timezone.now().strftime("%Y%m%d")
    code = period.code if period else "period"
    return _xlsx(build_benefits_extract(cases), f"DCollect benefits {code} {stamp}")


@analyst_required
def documents_register(request):
    period = _period()
    cases = _report_cases(request.user, period)
    stamp = timezone.now().strftime("%Y%m%d")
    code = period.code if period else "period"
    return _xlsx(build_documents_register(cases), f"DCollect documents {code} {stamp}")
