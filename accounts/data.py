"""Administrator tools to remove collected survey data without touching catalogues or audit history."""

from pathlib import Path

from django.conf import settings

from collection.models import (
    CaseDocument,
    CaseDocumentFile,
    ComparatorBenefitRow,
    ComparatorPayRow,
    CountyCase,
    IndividualResponse,
    StaffSurveyLink,
)

from .models import User

USER_AUDIT_FIELDS = (
    "username",
    "first_name",
    "last_name",
    "email",
    "role",
    "county",
    "phone",
    "job_title",
    "is_active",
    "must_change_password",
)


def _display(value):
    if value is None or value is False:
        return "No" if value is False else "—"
    if value is True:
        return "Yes"
    if hasattr(value, "name"):
        return value.name
    if hasattr(value, "get_role_display") and not isinstance(value, str):
        return str(value)
    return str(value)


def describe_user_changes(instance, form):
    """Human-readable account changes. Passwords are noted, never recorded."""
    data = form.cleaned_data
    if instance is None or not instance.pk:
        role = dict(User.Role.choices).get(data.get("role"), data.get("role"))
        county = data.get("county")
        bits = [f"Created {role} account “{data.get('username')}”"]
        if county:
            bits.append(f"linked to {county.name}")
        if data.get("password1"):
            bits.append("an initial password was set")
        return ". ".join(bits) + "."

    changes = []
    for name in USER_AUDIT_FIELDS:
        old = getattr(instance, name)
        new = data.get(name)
        if name == "role":
            old_label = instance.get_role_display()
            new_label = dict(User.Role.choices).get(new, new)
            if old != new:
                changes.append(f"role {old_label} → {new_label}")
            continue
        if _display(old) != _display(new):
            label = name.replace("_", " ")
            changes.append(f"{label}: {_display(old)} → {_display(new)}")
    if data.get("password1"):
        changes.append("password was reset by an administrator")
    if not changes:
        return "Saved the account with no field changes."
    return "Updated " + instance.username + ": " + "; ".join(changes) + "."


def _delete_file(fieldfile):
    if not fieldfile:
        return False
    name = getattr(fieldfile, "name", "") or ""
    if not name:
        return False
    try:
        fieldfile.delete(save=False)
        return True
    except Exception:
        try:
            path = Path(settings.MEDIA_ROOT) / name
            if path.is_file():
                path.unlink()
                return True
        except Exception:
            return False
    return False


def _purge_case_uploads(cases):
    removed = 0
    docs = CaseDocument.objects.filter(case__in=cases)
    for doc in docs:
        if doc.file and _delete_file(doc.file):
            removed += 1
        for att in doc.attachments.all():
            if att.file and _delete_file(att.file):
                removed += 1
    return removed


def purge_county_data(county):
    cases = CountyCase.objects.filter(county=county)
    case_count = cases.count()
    uploads = _purge_case_uploads(cases)
    staff = IndividualResponse.objects.filter(county=county).count()
    IndividualResponse.objects.filter(county=county).delete()
    StaffSurveyLink.objects.filter(county=county, is_open=False).delete()
    cases.delete()
    return {
        "county": county.name,
        "files": case_count,
        "uploads": uploads,
        "staff_responses": staff,
    }


def purge_user_collected_data(user):
    """
    Remove survey answers and uploads this person collected.
    Does not delete the login or the audit trail.
    County respondents: the whole county file for their county.
    Any role: documents they uploaded; consultant assignment is cleared.
    """
    result = {
        "username": user.username,
        "files": 0,
        "uploads": 0,
        "staff_responses": 0,
        "county": "",
        "unassigned": 0,
    }
    if user.county_id:
        stats = purge_county_data(user.county)
        result.update(
            {
                "files": stats["files"],
                "uploads": stats["uploads"],
                "staff_responses": stats["staff_responses"],
                "county": stats["county"],
            }
        )
    extra = 0
    own_docs = CaseDocument.objects.filter(uploaded_by=user)
    for doc in own_docs:
        if doc.file and _delete_file(doc.file):
            extra += 1
            doc.file = ""
        doc.uploaded_at = None
        doc.uploaded_by = None
        doc.received = ""
        doc.save(update_fields=["file", "uploaded_at", "uploaded_by", "received"])
    own_atts = CaseDocumentFile.objects.filter(uploaded_by=user)
    for att in own_atts:
        if att.file and _delete_file(att.file):
            extra += 1
        att.delete()
    result["uploads"] += extra
    unassigned = user.assigned_cases.update(assigned_consultant=None)
    result["unassigned"] = unassigned
    return result


def reset_collected_data():
    """
    Discard every county file, staff response, comparator figure and upload.
    Catalogues, users, site settings and the audit trail stay.
    """
    cases = CountyCase.objects.all()
    case_count = cases.count()
    uploads = _purge_case_uploads(cases)
    staff = IndividualResponse.objects.count()
    pay = ComparatorPayRow.objects.count()
    benefits = ComparatorBenefitRow.objects.count()
    IndividualResponse.objects.all().delete()
    StaffSurveyLink.objects.all().delete()
    ComparatorPayRow.objects.all().delete()
    ComparatorBenefitRow.objects.all().delete()
    cases.delete()
    return {
        "files": case_count,
        "uploads": uploads,
        "staff_responses": staff,
        "comparator_pay": pay,
        "comparator_benefits": benefits,
    }


def format_purge_summary(stats):
    bits = []
    if stats.get("county"):
        bits.append(stats["county"])
    bits.append(f"{stats.get('files', 0)} county file(s)")
    bits.append(f"{stats.get('uploads', 0)} upload(s)")
    bits.append(f"{stats.get('staff_responses', 0)} staff response(s)")
    if stats.get("unassigned"):
        bits.append(f"{stats['unassigned']} assignment(s) cleared")
    if stats.get("comparator_pay") is not None:
        bits.append(f"{stats['comparator_pay']} comparator pay row(s)")
    return ", ".join(bits)
