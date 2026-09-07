import secrets
from pathlib import Path

from catalog.models import (
    BenefitType,
    County,
    DocumentType,
    JobGroup,
    ValidationItem,
)

from .models import (
    BenefitRow,
    CaseDocument,
    CaseValidation,
    JobPayRow,
    Questionnaire,
    StaffSurveyLink,
)


def ensure_case_structure(case):
    Questionnaire.objects.get_or_create(case=case)
    groups = JobGroup.objects.filter(is_active=True, code__in=JobGroup.PAY_CODES)
    existing_groups = set(case.job_rows.values_list("job_group_id", flat=True))
    JobPayRow.objects.bulk_create(
        [JobPayRow(case=case, job_group=group) for group in groups if group.id not in existing_groups]
    )
    benefits = BenefitType.objects.filter(is_active=True)
    existing_benefits = set(case.benefit_rows.values_list("benefit_id", flat=True))
    BenefitRow.objects.bulk_create(
        [BenefitRow(case=case, benefit=b) for b in benefits if b.id not in existing_benefits]
    )
    docs = DocumentType.objects.filter(is_active=True)
    existing_docs = set(case.documents.values_list("document_type_id", flat=True))
    CaseDocument.objects.bulk_create(
        [CaseDocument(case=case, document_type=d) for d in docs if d.id not in existing_docs]
    )
    items = ValidationItem.objects.filter(is_active=True)
    existing_val = set(case.validations.values_list("item_id", flat=True))
    CaseValidation.objects.bulk_create(
        [CaseValidation(case=case, item=item) for item in items if item.id not in existing_val]
    )
    ensure_staff_link(case.county, case.survey_period)
    return case


def new_survey_token():
    return secrets.token_urlsafe(18)


def safe_attachment_name(name, fallback="file"):
    raw = (name or fallback).replace("\\", "/").split("/")[-1]
    raw = "".join(ch for ch in raw if ch not in "\x00\r\n")
    raw = raw.strip().strip(".")
    return raw or fallback


def iter_case_document_files(case):
    """Yield (document, folder_slug, file_name, file_field) for every uploaded file."""
    from django.utils.text import slugify

    docs = case.documents.select_related("document_type").prefetch_related("attachments")
    docs = docs.filter(document_type__is_active=True).order_by(
        "document_type__sort_order", "document_type__name"
    )
    for index, doc in enumerate(docs, 1):
        folder = slugify(doc.document_type.name) or doc.document_type.code or f"document-{index}"
        folder = f"{index:02d}-{folder}"
        files = list(doc.attachments.all())
        if doc.file:
            files.append(doc)
        for att in files:
            handle = att.file if getattr(att, "file", None) else None
            if not handle:
                continue
            name = att.display_name() if hasattr(att, "display_name") else Path(handle.name).name
            yield doc, folder, safe_attachment_name(name), handle


def ensure_staff_link(county, period, *, is_open=False):
    if period is None:
        return None
    if is_open:
        link, _ = StaffSurveyLink.objects.get_or_create(
            survey_period=period,
            is_open=True,
            defaults={"token": new_survey_token(), "is_active": True, "county": None},
        )
        return link
    if county is None:
        return None
    link, _ = StaffSurveyLink.objects.get_or_create(
        survey_period=period,
        county=county,
        is_open=False,
        defaults={"token": new_survey_token(), "is_active": True},
    )
    return link


def ensure_period_staff_links(period):
    if period is None:
        return
    ensure_staff_link(None, period, is_open=True)
    for county in County.objects.filter(is_active=True):
        ensure_staff_link(county, period)
