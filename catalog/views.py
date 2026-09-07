from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from collection.models import CountyCase
from collection.permissions import setup_required
from collection.questionnaire_spec import SECTION_TITLES

from .forms import (
    CollectionSettingsForm,
    OptionItemFormSet,
    OptionSetForm,
    QuestionItemForm,
    SiteSettingsForm,
    SurveyPeriodForm,
    catalog_form_class,
)
from .question_seed import seed_questions
from .models import (
    BenchmarkJob,
    BenefitType,
    ComparatorOrganization,
    County,
    DocumentType,
    JobFamily,
    JobGroup,
    OptionSet,
    QuestionItem,
    SRCGrade,
    SiteSettings,
    SurveyPeriod,
    ValidationItem,
)
from .registry import CATALOGS, get_catalog


def _counts():
    return {
        "counties": County.objects.filter(is_active=True).count(),
        "jobs": BenchmarkJob.objects.filter(is_active=True).count(),
        "benefits": BenefitType.objects.filter(is_active=True).count(),
        "documents": DocumentType.objects.filter(is_active=True).count(),
        "validation": ValidationItem.objects.filter(is_active=True).count(),
        "families": JobFamily.objects.filter(is_active=True).count(),
        "groups": JobGroup.objects.filter(is_active=True).count(),
        "grades": SRCGrade.objects.filter(is_active=True).count(),
        "comparators": ComparatorOrganization.objects.filter(is_active=True).count(),
        "option_sets": OptionSet.objects.count(),
        "periods": SurveyPeriod.objects.count(),
        "questions": QuestionItem.objects.filter(is_active=True).count(),
        "required_questions": QuestionItem.objects.filter(is_active=True, is_required=True).count(),
    }


@setup_required
def settings_home(request):
    instance = SiteSettings.load()
    can_edit_site = request.user.can_edit_site
    form_class = SiteSettingsForm if can_edit_site else CollectionSettingsForm
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Platform settings saved." if can_edit_site else "Collection settings saved.",
        )
        return redirect("catalog:settings")
    period = instance.active_survey_period or SurveyPeriod.objects.filter(is_active=True).first()
    open_ids = set()
    if period:
        open_ids = set(
            CountyCase.objects.filter(survey_period=period).values_list("county_id", flat=True)
        )
    counties = County.objects.filter(is_active=True)
    return render(
        request,
        "catalog/settings.html",
        {
            "form": form,
            "site": instance,
            "can_edit_site": can_edit_site,
            "counts": _counts(),
            "periods": SurveyPeriod.objects.all(),
            "catalogs": CATALOGS,
            "setup_section": "settings",
            "period": period,
            "counties": counties,
            "open_ids": open_ids,
        },
    )


@setup_required
def period_list(request):
    return render(
        request,
        "catalog/period_list.html",
        {"periods": SurveyPeriod.objects.all(), "setup_section": "periods"},
    )


@setup_required
def period_edit(request, pk=None):
    instance = get_object_or_404(SurveyPeriod, pk=pk) if pk else None
    form = SurveyPeriodForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        period = form.save()
        if period.is_active:
            settings_obj = SiteSettings.load()
            settings_obj.active_survey_period = period
            settings_obj.save(update_fields=["active_survey_period", "updated_at"])
        messages.success(request, "Survey period saved.")
        return redirect("catalog:periods")
    return render(
        request,
        "catalog/period_form.html",
        {"form": form, "instance": instance, "setup_section": "periods"},
    )


@setup_required
@require_POST
def period_activate(request, pk):
    period = get_object_or_404(SurveyPeriod, pk=pk)
    period.is_active = True
    period.save()
    settings_obj = SiteSettings.load()
    settings_obj.active_survey_period = period
    settings_obj.save(update_fields=["active_survey_period", "updated_at"])
    messages.success(request, f"{period.name} is now the active survey period.")
    return redirect("catalog:periods")


def _spec(key):
    try:
        return get_catalog(key)
    except KeyError as exc:
        raise Http404("Unknown catalogue") from exc


@setup_required
def catalog_list(request, key):
    spec = _spec(key)
    qs = spec["model"].objects.all()
    q = request.GET.get("q", "").strip()
    if q and spec.get("search"):
        query = Q()
        for field in spec["search"]:
            query |= Q(**{f"{field}__icontains": q})
        qs = qs.filter(query)
    display_rows = []
    for obj in qs:
        cells = []
        for field, _label in spec["columns"]:
            value = getattr(obj, field)
            if value is None:
                cells.append("—")
            elif isinstance(value, bool):
                cells.append("Yes" if value else "No")
            else:
                cells.append(str(value))
        display_rows.append((obj, cells))
    return render(
        request,
        "catalog/catalog_list.html",
        {
            "spec": spec,
            "key": key,
            "rows": display_rows,
            "q": q,
            "setup_section": "catalogs",
        },
    )


@setup_required
def catalog_edit(request, key, pk=None):
    spec = _spec(key)
    model = spec["model"]
    instance = get_object_or_404(model, pk=pk) if pk else None
    form_class = catalog_form_class(key)
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{spec['title']} saved.")
        return redirect("catalog:catalog_list", key=key)
    return render(
        request,
        "catalog/catalog_form.html",
        {
            "spec": spec,
            "key": key,
            "form": form,
            "instance": instance,
            "setup_section": "catalogs",
        },
    )


@setup_required
def option_list(request):
    return render(
        request,
        "catalog/option_list.html",
        {
            "sets": OptionSet.objects.prefetch_related("items"),
            "setup_section": "catalogs",
        },
    )


@setup_required
def option_edit(request, pk=None):
    instance = get_object_or_404(OptionSet, pk=pk) if pk else None
    form = OptionSetForm(request.POST or None, instance=instance)
    if request.method == "POST":
        if form.is_valid():
            option_set = form.save()
            formset = OptionItemFormSet(request.POST, instance=option_set)
            if formset.is_valid():
                formset.save()
                messages.success(request, "Dropdown list saved.")
                return redirect("catalog:options")
        else:
            formset = OptionItemFormSet(request.POST, instance=instance)
    else:
        formset = OptionItemFormSet(instance=instance)
    return render(
        request,
        "catalog/option_form.html",
        {
            "form": form,
            "formset": formset,
            "instance": instance,
            "setup_section": "catalogs",
        },
    )


@setup_required
def forms_home(request):
    seed_questions()
    settings_obj = SiteSettings.load()
    if request.method == "POST" and request.POST.get("update_rules"):
        settings_obj.jobs_require_src_equivalent = request.POST.get("jobs_require_src_equivalent") == "on"
        settings_obj.require_complete_to_submit = request.POST.get("require_complete_to_submit") == "on"
        settings_obj.save(
            update_fields=["jobs_require_src_equivalent", "require_complete_to_submit", "updated_at"]
        )
        messages.success(request, "Form rules saved.")
        return redirect("catalog:forms")
    sections = []
    for key, title in SECTION_TITLES.items():
        items = QuestionItem.objects.filter(section=key).order_by("sort_order", "label")
        sections.append(
            {
                "key": key,
                "title": title,
                "items": items,
                "required": items.filter(is_active=True, is_required=True).count(),
                "active": items.filter(is_active=True).count(),
            }
        )
    return render(
        request,
        "catalog/forms.html",
        {
            "setup_section": "forms",
            "sections": sections,
            "settings_obj": settings_obj,
            "job_count": BenchmarkJob.objects.filter(is_active=True).count(),
            "required_jobs": BenchmarkJob.objects.filter(is_active=True, is_required=True).count(),
            "benefit_count": BenefitType.objects.filter(is_active=True).count(),
            "required_benefits": BenefitType.objects.filter(is_active=True, is_required=True).count(),
            "doc_count": DocumentType.objects.filter(is_active=True).count(),
            "required_docs": DocumentType.objects.filter(is_active=True, is_required=True).count(),
            "required_question_count": QuestionItem.objects.filter(is_active=True, is_required=True).count(),
        },
    )


@setup_required
def question_list(request):
    seed_questions()
    section = (request.GET.get("section") or "a").lower()
    if section not in SECTION_TITLES:
        section = "a"
    items = QuestionItem.objects.filter(section=section).select_related("option_set")
    return render(
        request,
        "catalog/question_list.html",
        {
            "setup_section": "forms",
            "section": section,
            "section_title": SECTION_TITLES[section],
            "sections": SECTION_TITLES,
            "items": items,
        },
    )


@setup_required
def question_edit(request, pk=None):
    from django.urls import reverse

    instance = get_object_or_404(QuestionItem, pk=pk) if pk else None
    form = QuestionItemForm(request.POST or None, instance=instance)
    if not instance and not request.POST:
        initial_section = request.GET.get("section") or "a"
        if initial_section in SECTION_TITLES:
            form.fields["section"].initial = initial_section
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, "Question saved.")
        return redirect(reverse("catalog:questions") + f"?section={item.section}")
    return render(
        request,
        "catalog/question_form.html",
        {
            "form": form,
            "instance": instance,
            "setup_section": "forms",
        },
    )


@setup_required
@require_POST
def question_delete(request, pk):
    from django.urls import reverse

    item = get_object_or_404(QuestionItem, pk=pk)
    if item.is_builtin:
        messages.error(request, "Built-in survey questions cannot be deleted. Deactivate them instead.")
        return redirect("catalog:questions")
    section = item.section
    item.delete()
    messages.success(request, "Custom question removed.")
    return redirect(reverse("catalog:questions") + f"?section={section}")

