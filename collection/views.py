from io import BytesIO
from pathlib import Path
import zipfile

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from catalog.models import (
    BenchmarkJob,
    BenefitType,
    ComparatorOrganization,
    County,
    JobGroup,
    SiteSettings,
    SRCGrade,
    SurveyPeriod,
)
from reports.analysis import (
    build_analysis_rows,
    distribution,
    orgs_with_pay,
    rollup_rows,
    summarise_rows,
    unmatched_staff_count,
)

from .forms import (
    BenefitFormSet,
    CaseAssignForm,
    CertifyForm,
    ClarificationForm,
    ClarificationResponseForm,
    ComparatorBenefitForm,
    ComparatorOrgForm,
    ComparatorPayForm,
    DocumentMetaForm,
    IndividualResponseForm,
    JobPayFormSet,
    QuestionnaireForm,
    ValidationFormSet,
)
from accounts.audit import record_event
from accounts.models import AuditEntry

from .models import (
    CaseDocument,
    CaseDocumentFile,
    Clarification,
    ComparatorBenefitRow,
    ComparatorPayRow,
    CountyCase,
    IndividualResponse,
    StaffSurveyLink,
    log_event,
)
from .permissions import (
    analysis_required,
    analyst_required,
    case_required,
    get_visible_cases,
    setup_required,
)
from .questionnaire_spec import INTRO, SECTION_TITLES
from .services import (
    ensure_case_structure,
    ensure_period_staff_links,
    ensure_staff_link,
    iter_case_document_files,
    safe_attachment_name,
)

SECTIONS = [
    ("a", "A · Institution"),
    ("b", "B · Workforce"),
    ("c", "C · Policy"),
    ("d", "D · Structure"),
    ("e", "E · Allowances"),
    ("f", "F · Recruitment"),
    ("g", "G · Equity"),
    ("h", "H · Pay mix"),
    ("i", "I · Affordability"),
    ("j", "J · Documents"),
]


def _period(request):
    settings_obj = SiteSettings.load()
    if settings_obj.active_survey_period:
        return settings_obj.active_survey_period
    return SurveyPeriod.objects.filter(is_active=True).first()


def _county_can_edit(user, case, module=None):
    if user.can_configure or user.is_admin_role:
        return True
    if user.role == user.Role.COUNTY:
        allowed = case.unlocked_modules_for_county()
        if module is None:
            return bool(allowed)
        return module in allowed
    if user.can_review:
        return True
    return False


def _county_next_action(case, progress, open_clar_count):
    if open_clar_count:
        return {
            "title": "Answer open clarifications",
            "detail": "The consultant asked for more information before the file can be accepted.",
            "url_name": "collection:clarifications",
            "label": "Open clarifications",
        }
    if case.is_locked_for_county:
        return {
            "title": "Waiting for review",
            "detail": "This file is with the consultant. You will be able to edit it again if it is returned.",
            "url_name": "collection:case_hub",
            "label": "View file",
        }
    if progress["questionnaire"] < 100:
        return {
            "title": "Continue the questionnaire",
            "detail": "Complete sections A–J. Save each section as you go.",
            "url_name": "collection:questionnaire",
            "label": "Open questionnaire",
        }
    if progress["jobs"] < 100:
        return {
            "title": "Complete benchmark positions",
            "detail": "Enter the SRC equivalent, min/max basic and allowances, or mark a job not applicable.",
            "url_name": "collection:jobs",
            "label": "Open jobs",
        }
    if progress["benefits"] < 100:
        return {
            "title": "Complete the benefits matrix",
            "detail": "Mark each benefit Yes / No / Partial and add contribution notes.",
            "url_name": "collection:benefits",
            "label": "Open benefits",
        }
    if progress["documents"] < 100:
        return {
            "title": "Upload documents",
            "detail": "Attach the requested files, or mark an optional item not available.",
            "url_name": "collection:documents",
            "label": "Open documents",
        }
    if not progress["certified"]:
        return {
            "title": "Certify the file",
            "detail": "Add your name, designation and initials before submitting.",
            "url_name": "collection:certify",
            "label": "Certify",
        }
    return {
        "title": "Submit for review",
        "detail": "The file looks complete. Send it to the consultant.",
        "url_name": "collection:case_hub",
        "label": "Go to submit",
    }


def dashboard(request):
    period = _period(request)
    cases = get_visible_cases(request.user, period)
    stats = {
        "total": cases.count(),
        "draft": cases.filter(status=CountyCase.Status.DRAFT).count(),
        "submitted": cases.filter(status=CountyCase.Status.SUBMITTED).count(),
        "clarification": cases.filter(status=CountyCase.Status.CLARIFICATION).count(),
        "validated": cases.filter(
            status__in=[CountyCase.Status.VALIDATED, CountyCase.Status.IN_ANALYSIS]
        ).count(),
    }
    open_clarifications = list(
        Clarification.objects.filter(case__in=cases, resolved=False).select_related(
            "case", "case__county"
        )[:8]
    )
    recent = list(cases.order_by("-updated_at")[:8])
    queue = list(
        cases.filter(
            status__in=[CountyCase.Status.SUBMITTED, CountyCase.Status.CLARIFICATION]
        ).order_by("status", "updated_at")[:10]
    )
    my_case = None
    progress = None
    next_action = None
    my_clarifications = []
    if request.user.role == request.user.Role.COUNTY and request.user.county_id and period:
        my_case = cases.filter(county=request.user.county).first()
        if my_case:
            ensure_case_structure(my_case)
            progress = my_case.progress()
            my_clarifications = list(my_case.clarifications.filter(resolved=False)[:8])
            next_action = _county_next_action(my_case, progress, len(my_clarifications))

    setup = None
    comparator_summary = None
    if request.user.can_configure:
        active_counties = County.objects.filter(is_active=True).count()
        from accounts.models import User

        county_logins = User.objects.filter(
            role=User.Role.COUNTY, is_active=True, county__isnull=False
        ).values("county_id").distinct().count()
        setup = {
            "has_period": bool(period),
            "files": stats["total"],
            "counties": active_counties,
            "county_logins": county_logins,
        }
    if request.user.is_analyst_role and period:
        jobs_total = BenchmarkJob.objects.filter(is_active=True).count()
        orgs = ComparatorOrganization.objects.filter(is_active=True)
        filled_orgs = 0
        for org in orgs:
            n = ComparatorPayRow.objects.filter(
                organization=org, survey_period=period
            ).filter(
                Q(not_applicable=True)
                | Q(min_basic__isnull=False)
                | Q(max_basic__isnull=False)
                | Q(median_basic__isnull=False)
            ).count()
            if jobs_total and n:
                filled_orgs += 1
        comparator_summary = {
            "orgs": orgs.count(),
            "with_pay": filled_orgs,
        }

    hour = timezone.localtime().hour
    if hour < 12:
        greeting = "morning"
    elif hour < 17:
        greeting = "afternoon"
    else:
        greeting = "evening"

    return render(
        request,
        "collection/dashboard.html",
        {
            "greeting": greeting,
            "period": period,
            "stats": stats,
            "cases": recent,
            "queue": queue,
            "open_clarifications": open_clarifications,
            "my_case": my_case,
            "progress": progress,
            "next_action": next_action,
            "my_clarifications": my_clarifications,
            "setup": setup,
            "comparator_summary": comparator_summary,
        },
    )


@analyst_required
def questionnaire_list(request):
    period = _period(request)
    cases = get_visible_cases(request.user, period)
    q_filter = request.GET.get("q", "").strip()
    if q_filter:
        cases = cases.filter(county__name__icontains=q_filter)
    rows = []
    for case in cases:
        ensure_case_structure(case)
        questionnaire = case.get_questionnaire()
        section_state = []
        if questionnaire:
            section_state = [
                (key, label, questionnaire.section_complete(key)) for key, label in SECTIONS
            ]
        rows.append((case, case.progress(), section_state))
    return render(
        request,
        "collection/questionnaire_list.html",
        {
            "rows": rows,
            "period": period,
            "q": q_filter,
        },
    )


@analyst_required
def case_list(request):
    period = _period(request)
    cases = get_visible_cases(request.user, period)
    status = request.GET.get("status")
    if status:
        cases = cases.filter(status=status)
    q = request.GET.get("q", "").strip()
    if q:
        cases = cases.filter(county__name__icontains=q)
    rows = []
    for case in cases:
        ensure_case_structure(case)
        rows.append((case, case.progress()))
    open_ids = set(cases.values_list("county_id", flat=True)) if period else set()
    return render(
        request,
        "collection/case_list.html",
        {
            "rows": rows,
            "period": period,
            "status": status or "",
            "q": q,
            "counties": County.objects.filter(is_active=True),
            "open_ids": open_ids,
        },
    )


@setup_required
@require_POST
def open_period_cases(request):
    period = _period(request)
    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("//") or not next_url.startswith("/"):
        next_url = ""
    if not period:
        messages.error(request, "Create and activate a survey period first.")
        return redirect("catalog:settings")
    ids = [pk for pk in request.POST.getlist("county") if str(pk).isdigit()]
    counties = County.objects.filter(is_active=True)
    if ids:
        counties = counties.filter(pk__in=ids)
        if not counties.exists():
            messages.error(request, "Select at least one county.")
            return redirect(next_url or "catalog:settings")
    created = 0
    names = []
    for county in counties:
        case, was_created = CountyCase.objects.get_or_create(county=county, survey_period=period)
        ensure_case_structure(case)
        if was_created:
            created += 1
            names.append(county.name)
    if ids:
        if created:
            messages.success(
                request,
                f"Opened {created} file(s) for {period.name}: {', '.join(names)}.",
            )
        else:
            messages.info(request, "Those counties already have a file for this period.")
    else:
        messages.success(request, f"County files ready. {created} new file(s) opened for {period.name}.")
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect("collection:cases")


@case_required
def case_hub(request, case):
    ensure_case_structure(case)
    progress = case.progress()
    assign_form = None
    if request.user.can_configure:
        assign_form = CaseAssignForm(request.POST or None, instance=case)
        if request.method == "POST" and assign_form.is_valid():
            assign_form.save()
            log_event(case, request.user, "assignment updated")
            messages.success(request, "Assignment saved.")
            return redirect("collection:case_hub", pk=case.pk)
    clarifications = case.clarifications.select_related("created_by")[:12]
    events = case.events.select_related("actor")[:12]
    individual_count = IndividualResponse.objects.filter(
        county=case.county, survey_period=case.survey_period
    ).count()
    document_file_count = sum(
        len(doc.all_files())
        for doc in case.documents.filter(document_type__is_active=True).prefetch_related("attachments")
    )
    return render(
        request,
        "collection/case_hub.html",
        {
            "case": case,
            "progress": progress,
            "assign_form": assign_form,
            "clarifications": clarifications,
            "events": events,
            "can_edit": _county_can_edit(request.user, case),
            "sections": SECTIONS,
            "individual_count": individual_count,
            "document_file_count": document_file_count,
        },
    )


@case_required
def questionnaire(request, case):
    ensure_case_structure(case)
    q = case.questionnaire
    section = request.GET.get("section", "a").lower()
    if section not in dict(SECTIONS):
        section = "a"
    can_edit = _county_can_edit(request.user, case, "questionnaire")
    form = QuestionnaireForm(
        request.POST or None, instance=q, section=section
    )
    if request.method == "POST":
        if not can_edit:
            messages.error(request, "This file is locked. You can only edit the questionnaire if a clarification was requested on it.")
            return redirect("collection:questionnaire", pk=case.pk)
        if form.is_valid():
            form.save()
            log_event(case, request.user, "questionnaire saved", f"Section {section.upper()}")
            messages.success(request, f"Section {section.upper()} saved.")
            if request.POST.get("stay"):
                return redirect(f"{request.path}?section={section}")
            keys = [k for k, _ in SECTIONS]
            idx = keys.index(section)
            if idx + 1 < len(keys):
                return redirect(f"{request.path}?section={keys[idx + 1]}")
            return redirect("collection:case_hub", pk=case.pk)
    section_state = [(key, label, q.section_complete(key)) for key, label in SECTIONS]
    return render(
        request,
        "collection/questionnaire.html",
        {
            "case": case,
            "form": form,
            "section": section,
            "section_title": SECTION_TITLES.get(section, ""),
            "intro": INTRO,
            "sections": section_state,
            "can_edit": can_edit,
            "total_employees": q.total_employees(),
        },
    )


@case_required
def jobs(request, case):
    ensure_case_structure(case)
    can_edit = _county_can_edit(request.user, case, "jobs")
    require_src = SiteSettings.load().jobs_require_src_equivalent
    formset = JobPayFormSet(
        request.POST or None,
        instance=case,
        queryset=case.job_rows.select_related("job_group")
        .filter(job_group__code__in=JobGroup.PAY_CODES)
        .order_by("job_group__sort_order", "job_group__code"),
        form_kwargs={"require_src": require_src},
    )
    if request.method == "POST":
        if not can_edit:
            messages.error(request, "This file is locked.")
            return redirect("collection:jobs", pk=case.pk)
        if formset.is_valid():
            formset.save()
            log_event(case, request.user, "benchmark positions saved")
            messages.success(request, "Benchmark positions saved.")
            return redirect("collection:jobs", pk=case.pk)
        messages.error(request, "Some job rows could not be saved. Check the highlighted fields.")
    return render(
        request,
        "collection/jobs.html",
        {"case": case, "formset": formset, "can_edit": can_edit, "require_src": require_src},
    )


@case_required
def benefits(request, case):
    ensure_case_structure(case)
    can_edit = _county_can_edit(request.user, case, "benefits")
    formset = BenefitFormSet(
        request.POST or None,
        instance=case,
        queryset=case.benefit_rows.select_related("benefit").filter(benefit__is_active=True),
    )
    if request.method == "POST":
        if not can_edit:
            messages.error(request, "This file is locked.")
            return redirect("collection:benefits", pk=case.pk)
        if formset.is_valid():
            formset.save()
            log_event(case, request.user, "benefits saved")
            messages.success(request, "Benefits matrix saved.")
            return redirect("collection:benefits", pk=case.pk)
        messages.error(request, "Some benefit rows could not be saved. Check the highlighted fields.")
    return render(
        request,
        "collection/benefits.html",
        {"case": case, "formset": formset, "can_edit": can_edit},
    )


def _save_document_uploads(doc, uploads, user):
    max_mb = SiteSettings.load().max_upload_mb or 10
    saved = 0
    errors = []
    for upload in uploads:
        if not upload:
            continue
        suffix = Path(upload.name).suffix.lower()
        if suffix not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            errors.append(f"{upload.name} is not an allowed file type.")
            continue
        if upload.size > max_mb * 1024 * 1024:
            errors.append(f"{upload.name} exceeds the {max_mb} MB limit.")
            continue
        CaseDocumentFile.objects.create(
            document=doc,
            file=upload,
            original_name=Path(upload.name).name,
            uploaded_at=timezone.now(),
            uploaded_by=user,
        )
        saved += 1
    if saved:
        cache = getattr(doc, "_prefetched_objects_cache", None)
        if cache is not None:
            cache.pop("attachments", None)
        doc.not_available = False
        doc.uploaded_at = timezone.now()
        doc.uploaded_by = user
        if not doc.received:
            doc.received = "Yes"
        doc.save(update_fields=["not_available", "uploaded_at", "uploaded_by", "received"])
    return saved, errors


@case_required
def documents(request, case):
    ensure_case_structure(case)
    can_edit = _county_can_edit(request.user, case, "documents")
    docs = case.documents.select_related("document_type").filter(document_type__is_active=True).prefetch_related("attachments")
    if request.method == "POST" and can_edit:
        doc = get_object_or_404(docs, pk=request.POST.get("doc_id"))
        uploads = list(request.FILES.getlist("files"))
        if request.FILES.get("file"):
            uploads.append(request.FILES.get("file"))
        meta = DocumentMetaForm(request.POST, instance=doc, prefix=f"d{doc.pk}")
        saved_n, errors = _save_document_uploads(doc, uploads, request.user) if uploads else (0, [])
        for err in errors:
            messages.error(request, err)
        if meta.is_valid():
            saved = meta.save(commit=False)
            if saved_n:
                saved.not_available = False
                if not saved.received:
                    saved.received = "Yes"
            if getattr(saved, "not_available", False) and saved.document_type.is_required:
                saved.not_available = False
            saved.save()
            log_event(case, request.user, "document updated", doc.document_type.name)
            if saved_n:
                messages.success(
                    request,
                    f"{doc.document_type.name}: saved {saved_n} file{'s' if saved_n != 1 else ''}.",
                )
            else:
                messages.success(request, f"{doc.document_type.name} updated.")
        elif saved_n:
            log_event(case, request.user, "document uploaded", doc.document_type.name)
            messages.success(request, f"{doc.document_type.name}: files saved. Check the notes fields.")
        elif not errors:
            shown = False
            for err_list in meta.errors.values():
                for err in err_list:
                    messages.error(request, f"{doc.document_type.name}: {err}")
                    shown = True
            if not shown:
                messages.error(request, "Could not save document notes.")
        return redirect("collection:documents", pk=case.pk)
    rows = [(doc, DocumentMetaForm(instance=doc, prefix=f"d{doc.pk}")) for doc in docs]
    return render(
        request,
        "collection/documents.html",
        {"case": case, "rows": rows, "can_edit": can_edit},
    )


@case_required
def download_document(request, case, doc_id):
    doc = get_object_or_404(case.documents.select_related("document_type"), pk=doc_id)
    attachment = doc.attachments.order_by("id").first()
    target = attachment.file if attachment else doc.file
    if not target:
        raise Http404("No file has been uploaded for this document.")
    try:
        handle = target.open("rb")
    except FileNotFoundError:
        raise Http404("The uploaded file is no longer on the server.")
    filename = safe_attachment_name(
        attachment.display_name() if attachment else Path(target.name).name
    )
    log_event(case, request.user, "document downloaded", f"{doc.document_type.name}: {filename}")
    return FileResponse(handle, as_attachment=True, filename=filename)


@case_required
def download_document_file(request, case, doc_id, file_id):
    doc = get_object_or_404(case.documents, pk=doc_id)
    attachment = get_object_or_404(doc.attachments, pk=file_id)
    if not attachment.file:
        raise Http404("No file has been uploaded.")
    try:
        handle = attachment.file.open("rb")
    except FileNotFoundError:
        raise Http404("The uploaded file is no longer on the server.")
    name = safe_attachment_name(attachment.display_name())
    log_event(case, request.user, "document file downloaded", f"{doc.document_type.name}: {name}")
    return FileResponse(handle, as_attachment=True, filename=name)


@case_required
@require_POST
def delete_document_file(request, case, doc_id, file_id):
    if not _county_can_edit(request.user, case, "documents"):
        messages.error(request, "This file is locked.")
        return redirect("collection:documents", pk=case.pk)
    doc = get_object_or_404(case.documents.select_related("document_type"), pk=doc_id)
    attachment = get_object_or_404(doc.attachments, pk=file_id)
    name = attachment.display_name()
    if attachment.file:
        attachment.file.delete(save=False)
    attachment.delete()
    log_event(case, request.user, "document file removed", f"{doc.document_type.name}: {name}")
    messages.success(request, f"Removed {name}.")
    return redirect("collection:documents", pk=case.pk)


@case_required
def download_case_files(request, case):
    buffer = BytesIO()
    count = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        used = set()
        for _doc, folder, name, handle_file in iter_case_document_files(case):
            zip_name = f"{folder}/{name}"
            suffix = 2
            while zip_name in used:
                stem = Path(name).stem
                ext = Path(name).suffix
                zip_name = f"{folder}/{stem}-{suffix}{ext}"
                suffix += 1
            used.add(zip_name)
            try:
                with handle_file.open("rb") as handle:
                    archive.writestr(zip_name, handle.read())
                count += 1
            except Exception:
                continue
    if not count:
        messages.error(request, "This county file has no uploaded documents to download.")
        return redirect("collection:documents", pk=case.pk)
    stamp = timezone.now().strftime("%Y%m%d")
    filename = f"{slugify(case.county.name)}-documents-{stamp}.zip"
    log_event(case, request.user, "documents zip downloaded", f"{count} file{'s' if count != 1 else ''}")
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@case_required
def validation(request, case):
    if not request.user.can_review:
        messages.error(request, "Only consultants and administrators can complete validation.")
        return redirect("collection:case_hub", pk=case.pk)
    ensure_case_structure(case)
    formset = ValidationFormSet(
        request.POST or None,
        instance=case,
        queryset=case.validations.select_related("item").filter(item__is_active=True),
    )
    if request.method == "POST" and formset.is_valid():
        rows = formset.save(commit=False)
        for row in rows:
            row.updated_by = request.user
            row.save()
        log_event(case, request.user, "validation updated")
        messages.success(request, "Validation checklist saved.")
        return redirect("collection:validation", pk=case.pk)
    return render(
        request,
        "collection/validation.html",
        {"case": case, "formset": formset, "progress": case.progress()},
    )


@case_required
def certify(request, case):
    can_edit = _county_can_edit(request.user, case, "certify")
    form = CertifyForm(request.POST or None, instance=case)
    if request.method == "POST" and can_edit and form.is_valid():
        obj = form.save(commit=False)
        obj.certified_at = timezone.now()
        obj.save()
        log_event(case, request.user, "file certified", obj.certified_name)
        messages.success(request, "County file certified.")
        return redirect("collection:case_hub", pk=case.pk)
    return render(
        request,
        "collection/certify.html",
        {"case": case, "form": form, "can_edit": can_edit, "progress": case.progress()},
    )


@case_required
@require_POST
def submit_case(request, case):
    if not _county_can_edit(request.user, case):
        messages.error(request, "This file is locked. You can only edit sections with an open clarification.")
        return redirect("collection:case_hub", pk=case.pk)
    settings_obj = SiteSettings.load()
    if settings_obj.require_certification_to_submit and not case.certified_at:
        messages.error(request, "Certify the file before submitting.")
        return redirect("collection:certify", pk=case.pk)
    if settings_obj.require_complete_to_submit:
        progress = case.progress()
        required = progress.get("required") or progress
        missing = []
        if required["questionnaire"] < 100:
            missing.append("questionnaire")
        if required["jobs"] < 100:
            missing.append("benchmark jobs")
        if required["benefits"] < 100:
            missing.append("benefits")
        if required["documents"] < 100:
            missing.append("required documents")
        if missing:
            messages.error(
                request,
                "Complete the required items before submitting: " + ", ".join(missing) + ".",
            )
            return redirect("collection:case_hub", pk=case.pk)
    case.mark_submitted(request.user)
    log_event(case, request.user, "submitted for review")
    messages.success(request, "County file submitted for consultant review.")
    return redirect("collection:case_hub", pk=case.pk)


@case_required
@require_POST
def reopen_case(request, case):
    if not request.user.can_review:
        messages.error(request, "Only reviewers can return a file.")
        return redirect("collection:case_hub", pk=case.pk)
    case.request_clarification()
    log_event(case, request.user, "returned for clarification")
    messages.success(request, "File returned to the county for clarification.")
    return redirect("collection:case_hub", pk=case.pk)


@case_required
@require_POST
def validate_case(request, case):
    if not request.user.can_review:
        messages.error(request, "Only reviewers can validate a file.")
        return redirect("collection:case_hub", pk=case.pk)
    if not case.validation_complete():
        messages.error(
            request,
            "Fill a status on every validation item before marking this file as validated.",
        )
        return redirect("collection:validation", pk=case.pk)
    case.mark_validated(request.user)
    log_event(case, request.user, "validated")
    messages.success(request, "County file marked as validated.")
    return redirect("collection:case_hub", pk=case.pk)


@case_required
def clarifications(request, case):
    form = ClarificationForm(request.POST or None) if request.user.can_review else None
    if request.method == "POST" and form and form.is_valid():
        item = form.save(commit=False)
        item.case = case
        item.created_by = request.user
        item.save()
        case.request_clarification()
        log_event(case, request.user, "clarification requested", item.module)
        messages.success(request, "Clarification sent to the county.")
        return redirect("collection:clarifications", pk=case.pk)
    items = case.clarifications.select_related("created_by")
    return render(
        request,
        "collection/clarifications.html",
        {
            "case": case,
            "form": form,
            "items": items,
            "response_form": ClarificationResponseForm(),
            "can_respond": request.user.role == request.user.Role.COUNTY
            or request.user.can_review,
        },
    )


@case_required
@require_POST
def resolve_clarification(request, case):
    item = get_object_or_404(case.clarifications, pk=request.POST.get("item_id"))
    form = ClarificationResponseForm(request.POST)
    if form.is_valid():
        item.response = form.cleaned_data["response"]
        item.resolved = True
        item.resolved_at = timezone.now()
        item.save()
        log_event(case, request.user, "clarification answered", item.module)
        messages.success(request, "Response recorded.")
    return redirect("collection:clarifications", pk=case.pk)


def _comparator_stats(orgs, period):
    jobs_total = BenchmarkJob.objects.filter(is_active=True).count()
    benefits_total = BenefitType.objects.filter(is_active=True).count()
    rows = []
    for org in orgs:
        pay_qs = ComparatorPayRow.objects.filter(organization=org, survey_period=period) if period else ComparatorPayRow.objects.none()
        pay_filled = pay_qs.filter(
            Q(not_applicable=True)
            | Q(min_basic__isnull=False)
            | Q(max_basic__isnull=False)
            | Q(median_basic__isnull=False)
        ).count()
        benefit_qs = ComparatorBenefitRow.objects.filter(organization=org, survey_period=period) if period else ComparatorBenefitRow.objects.none()
        benefit_filled = benefit_qs.exclude(provided="").count()
        rows.append(
            {
                "org": org,
                "pay_filled": pay_filled,
                "pay_total": jobs_total,
                "benefit_filled": benefit_filled,
                "benefit_total": benefits_total,
            }
        )
    return rows


@analyst_required
def comparator_list(request):
    period = _period(request)
    orgs = ComparatorOrganization.objects.all()
    form = ComparatorOrgForm(request.POST or None) if request.user.can_review else None
    if request.method == "POST" and form and form.is_valid():
        form.save()
        messages.success(request, "Comparator organisation saved.")
        return redirect("collection:comparators")
    return render(
        request,
        "collection/comparators.html",
        {
            "orgs": orgs,
            "org_rows": _comparator_stats(orgs, period),
            "form": form,
            "can_edit": request.user.can_review,
            "can_delete": request.user.can_edit_site,
            "period": period,
        },
    )


@analyst_required
def comparator_edit(request, org_id):
    org = get_object_or_404(ComparatorOrganization, pk=org_id)
    if not request.user.can_review:
        messages.error(request, "Only consultants and administrators can edit comparator details.")
        return redirect("collection:comparators")
    form = ComparatorOrgForm(request.POST or None, instance=org)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{org.name} saved.")
        return redirect("collection:comparators")
    return render(
        request,
        "collection/comparator_form.html",
        {"form": form, "org": org, "can_edit": True, "can_delete": request.user.can_edit_site},
    )


@analyst_required
@require_POST
def comparator_delete(request, org_id):
    if not request.user.can_edit_site:
        messages.error(request, "Only a platform administrator can delete a comparator.")
        return redirect("collection:comparators")
    org = get_object_or_404(ComparatorOrganization, pk=org_id)
    confirm = (request.POST.get("confirm") or "").strip()
    if confirm.casefold() != org.name.casefold():
        messages.error(request, f'Type “{org.name}” exactly to confirm deletion.')
        return redirect("collection:comparator_edit", org_id=org.pk)
    name = org.name
    pay_count = org.pay_rows.count()
    benefit_count = org.benefit_rows.count()
    org.delete()
    record_event(
        action="collection:comparator_delete",
        summary=f"Deleted comparator {name}",
        request=request,
        category=AuditEntry.Category.COMPARATORS,
        detail=f"Removed the organisation and {pay_count} pay row(s) and {benefit_count} benefit row(s).",
        target_label=name,
    )
    messages.success(request, f"{name} has been deleted, including its pay and benefits figures.")
    return redirect("collection:comparators")


@analyst_required
def comparator_pay(request, org_id):
    period = _period(request)
    org = get_object_or_404(ComparatorOrganization, pk=org_id)
    if not period:
        messages.error(request, "Activate a survey period first.")
        return redirect("collection:comparators")
    jobs = BenchmarkJob.objects.filter(is_active=True)
    existing = {
        row.job_id: row
        for row in ComparatorPayRow.objects.filter(organization=org, survey_period=period)
    }
    for job in jobs:
        if job.id not in existing:
            existing[job.id] = ComparatorPayRow.objects.create(
                organization=org, survey_period=period, job=job
            )
    rows = []
    if request.method == "POST" and request.user.can_review:
        ok = True
        for job in jobs:
            instance = existing[job.id]
            form = ComparatorPayForm(request.POST, instance=instance, prefix=f"j{job.id}")
            if form.is_valid():
                form.save()
            else:
                ok = False
            rows.append((job, form))
        if ok:
            messages.success(request, f"Pay table saved for {org.name}.")
            return redirect("collection:comparator_pay", org_id=org.id)
        messages.error(request, "Some job rows could not be saved. Check the highlighted fields.")
    else:
        rows = [
            (job, ComparatorPayForm(instance=existing[job.id], prefix=f"j{job.id}"))
            for job in jobs
        ]
    return render(
        request,
        "collection/comparator_pay.html",
        {"org": org, "period": period, "rows": rows, "can_edit": request.user.can_review},
    )


@analyst_required
def comparator_benefits(request, org_id):
    period = _period(request)
    org = get_object_or_404(ComparatorOrganization, pk=org_id)
    benefits = BenefitType.objects.filter(is_active=True)
    existing = {
        row.benefit_id: row
        for row in ComparatorBenefitRow.objects.filter(organization=org, survey_period=period)
    }
    for benefit in benefits:
        if benefit.id not in existing:
            existing[benefit.id] = ComparatorBenefitRow.objects.create(
                organization=org, survey_period=period, benefit=benefit
            )
    rows = []
    if request.method == "POST" and request.user.can_review:
        ok = True
        for benefit in benefits:
            instance = existing[benefit.id]
            form = ComparatorBenefitForm(request.POST, instance=instance, prefix=f"b{benefit.id}")
            if form.is_valid():
                form.save()
            else:
                ok = False
            rows.append((benefit, form))
        if ok:
            messages.success(request, f"Benefits saved for {org.name}.")
            return redirect("collection:comparator_benefits", org_id=org.id)
    else:
        rows = [
            (benefit, ComparatorBenefitForm(instance=existing[benefit.id], prefix=f"b{benefit.id}"))
            for benefit in benefits
        ]
    return render(
        request,
        "collection/comparator_benefits.html",
        {"org": org, "period": period, "rows": rows, "can_edit": request.user.can_review},
    )


@analysis_required
def analysis(request):
    period = _period(request)
    measure = request.GET.get("measure", "basic")
    if measure not in {"basic", "total"}:
        measure = "basic"
    show_empty = request.GET.get("show") == "all"
    cases = (
        get_visible_cases(request.user, period)
        .annotate(
            filled_jobs=Count(
                "job_rows",
                filter=Q(job_rows__not_applicable=False)
                & Q(job_rows__job_group__code__in=JobGroup.PAY_CODES)
                & (
                    Q(job_rows__min_basic__isnull=False)
                    | Q(job_rows__max_basic__isnull=False)
                ),
            )
        )
        .order_by("-filled_jobs", "county__name")
    )
    selected_id = request.GET.get("case")
    case = cases.filter(pk=selected_id).first() if selected_id else cases.first()
    if case:
        ensure_case_structure(case)
    configured = ComparatorOrganization.objects.filter(
        is_active=True, include_in_market_median=True
    ).order_by("sort_order", "name")
    orgs = orgs_with_pay(configured, period) if period else []
    rows = build_analysis_rows(case, orgs, period, measure=measure) if case else []
    visible_rows = rows if show_empty else [r for r in rows if r["has_county"]]
    return render(
        request,
        "collection/analysis.html",
        {
            "period": period,
            "cases": cases,
            "case": case,
            "orgs": orgs,
            "rows": visible_rows,
            "measure": measure,
            "show_empty": show_empty,
            "summary": summarise_rows(rows),
            "unmatched_staff": unmatched_staff_count(case, period) if case else 0,
            "src_rollups": rollup_rows(visible_rows, "src_equivalent"),
        },
    )


def help_centre(request):
    if not request.user.can_see_help:
        return HttpResponseForbidden("This page is not available for your role.")
    return render(request, "collection/help.html", {"role": getattr(request.user, "role", "")})


def public_survey(request, token):
    link = get_object_or_404(StaffSurveyLink, token=token, is_active=True)
    period = link.survey_period
    locked = None if link.is_open else link.county
    if request.method == "POST":
        form = IndividualResponseForm(request.POST, locked_county=locked)
        if form.is_valid():
            response = form.save(commit=False)
            response.link = link
            response.survey_period = period
            if locked is not None:
                response.county = locked
            if response.job_id and not response.job_title:
                response.job_title = response.job.title
            response.save()
            return redirect("collection:survey_thanks", token=token)
    else:
        form = IndividualResponseForm(locked_county=locked)
    return render(
        request,
        "collection/public_survey.html",
        {
            "form": form,
            "link": link,
            "period": period,
            "locked_county": locked,
        },
    )


def public_survey_thanks(request, token):
    link = get_object_or_404(StaffSurveyLink, token=token)
    return render(
        request,
        "collection/public_survey_thanks.html",
        {"link": link, "locked_county": None if link.is_open else link.county},
    )


@setup_required
def staff_survey_links(request):
    period = _period(request)
    ensure_period_staff_links(period)
    open_link = StaffSurveyLink.objects.filter(survey_period=period, is_open=True).first() if period else None
    county_links = []
    if period:
        county_links = (
            StaffSurveyLink.objects.filter(survey_period=period, is_open=False)
            .select_related("county")
            .order_by("county__name")
        )
    counts = {
        row["county_id"]: row["n"]
        for row in IndividualResponse.objects.filter(survey_period=period)
        .values("county_id")
        .annotate(n=Count("id"))
    } if period else {}
    rows = [(link, counts.get(link.county_id, 0)) for link in county_links]
    return render(
        request,
        "collection/staff_links.html",
        {
            "period": period,
            "open_link": open_link,
            "rows": rows,
            "total": sum(counts.values()) if counts else 0,
            "setup_section": "staff",
        },
    )


@case_required
def individual_responses(request, case):
    ensure_staff_link(case.county, case.survey_period)
    link = StaffSurveyLink.objects.filter(
        county=case.county, survey_period=case.survey_period, is_open=False
    ).first()
    responses = IndividualResponse.objects.filter(
        county=case.county, survey_period=case.survey_period
    ).select_related("job", "job__job_group")
    basics = distribution([row.current_basic for row in responses])
    totals = distribution([row.total_cash() for row in responses])
    stats = {
        "n": responses.count(),
        "p25": basics["p25"],
        "p50": basics["p50"],
        "p75": basics["p75"],
        "total_p50": totals["p50"],
    }
    return render(
        request,
        "collection/individuals.html",
        {
            "case": case,
            "link": link,
            "responses": responses,
            "stats": stats,
            "can_edit": False,
        },
    )
