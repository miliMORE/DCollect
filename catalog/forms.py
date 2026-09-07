from django import forms
from django.utils.text import slugify

from .models import OptionItem, OptionSet, QuestionItem, SiteSettings, SurveyPeriod
from .ordering import next_sort_order
from .registry import get_catalog


def style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "checkbox")
        elif isinstance(field.widget, forms.Textarea):
            field.widget.attrs.setdefault("class", "input")
            field.widget.attrs.setdefault("rows", field.widget.attrs.get("rows", 3))
        else:
            field.widget.attrs.setdefault("class", "input")


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "short_name",
            "survey_title",
            "org_name",
            "client_name",
            "support_email",
            "active_survey_period",
            "max_upload_mb",
            "require_certification_to_submit",
            "allow_county_see_analysis",
            "purpose_text",
            "how_to_use_text",
            "confidentiality_text",
        ]
        labels = {
            "short_name": "Product name",
            "survey_title": "Survey title",
            "org_name": "Consultant / implementing firm",
            "client_name": "Client",
            "support_email": "Support email",
            "active_survey_period": "Active survey period",
            "max_upload_mb": "Maximum upload size (MB)",
            "require_certification_to_submit": "Require certification before submit",
            "allow_county_see_analysis": "Let county users open live analysis",
            "purpose_text": "Purpose (shown on county packs)",
            "how_to_use_text": "How to use (shown on county packs)",
            "confidentiality_text": "Confidentiality statement",
        }
        help_texts = {
            "short_name": "Product name shown in the sidebar. It is DCollect — no s at the end.",
            "survey_title": "Full study title on the sign-in page and in Excel packs.",
            "org_name": "BINSTOPEJ or the firm running the survey.",
            "client_name": "CPSB-NCF or the commissioning body.",
            "support_email": "Where counties write if they cannot sign in.",
            "active_survey_period": "The period dashboards, files and reports use.",
            "max_upload_mb": "Applies to payroll extracts, salary structures and other attachments.",
            "require_certification_to_submit": "County must sign the file before it can be submitted.",
            "allow_county_see_analysis": "Leave off unless a county is allowed to see market figures.",
        }
        widgets = {
            "purpose_text": forms.Textarea(attrs={"rows": 5}),
            "how_to_use_text": forms.Textarea(attrs={"rows": 3}),
            "confidentiality_text": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["active_survey_period"].queryset = SurveyPeriod.objects.all()
        self.fields["active_survey_period"].required = False
        style_fields(self)

    def clean_short_name(self):
        name = (self.cleaned_data.get("short_name") or "").strip()
        compact = name.lower().replace(" ", "").replace("-", "")
        if compact in {"dcollects"}:
            return "DCollect"
        return name or "DCollect"

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit and obj.active_survey_period_id:
            SurveyPeriod.objects.filter(pk=obj.active_survey_period_id).update(is_active=True)
            SurveyPeriod.objects.exclude(pk=obj.active_survey_period_id).update(is_active=False)
        return obj


class CollectionSettingsForm(forms.ModelForm):

    class Meta:
        model = SiteSettings
        fields = [
            "active_survey_period",
            "max_upload_mb",
            "require_certification_to_submit",
        ]
        labels = {
            "active_survey_period": "Active survey period",
            "max_upload_mb": "Maximum upload size (MB)",
            "require_certification_to_submit": "Require certification before submit",
        }
        help_texts = {
            "active_survey_period": "The period dashboards, files and reports use.",
            "max_upload_mb": "Applies to payroll extracts, salary structures and other attachments.",
            "require_certification_to_submit": "County must sign the file before it can be submitted.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["active_survey_period"].queryset = SurveyPeriod.objects.all()
        self.fields["active_survey_period"].required = False
        style_fields(self)

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit and obj.active_survey_period_id:
            SurveyPeriod.objects.filter(pk=obj.active_survey_period_id).update(is_active=True)
            SurveyPeriod.objects.exclude(pk=obj.active_survey_period_id).update(is_active=False)
        return obj


class SurveyPeriodForm(forms.ModelForm):
    class Meta:
        model = SurveyPeriod
        fields = ["name", "code", "start_date", "end_date", "is_active", "notes"]
        help_texts = {
            "code": "Short slug used in download filenames, for example 2026-review.",
            "is_active": "Only one period can be active. Saving this as active updates platform settings.",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


def catalog_form_class(key):
    spec = get_catalog(key)

    class CatalogForm(forms.ModelForm):
        class Meta:
            model = spec["model"]
            fields = spec["fields"]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields.pop("sort_order", None)
            style_fields(self)
            if "code" in self.fields and not self.instance.pk:
                self.fields["code"].required = False
                self.fields["code"].help_text = (
                    self.fields["code"].help_text
                    or "Leave blank to generate from the name or title."
                )

        def clean(self):
            cleaned = super().clean()
            code = cleaned.get("code")
            if not code:
                seed = cleaned.get("name") or cleaned.get("title") or cleaned.get("code")
                if seed:
                    cleaned["code"] = slugify(str(seed))[:50]
                    self.cleaned_data["code"] = cleaned["code"]
            return cleaned

        def save(self, commit=True):
            obj = super().save(commit=False)
            if not obj.pk and hasattr(obj, "sort_order") and not obj.sort_order:
                obj.sort_order = next_sort_order(spec["model"].objects.all())
            if commit:
                obj.save()
            return obj

    CatalogForm.__name__ = f"{spec['model'].__name__}Form"
    return CatalogForm


class OptionSetForm(forms.ModelForm):
    class Meta:
        model = OptionSet
        fields = ["code", "name", "help_text"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class OptionItemForm(forms.ModelForm):
    class Meta:
        model = OptionItem
        fields = ["value", "label", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.sort_order:
            qs = OptionItem.objects.filter(option_set_id=obj.option_set_id)
            if obj.pk:
                qs = qs.exclude(pk=obj.pk)
            obj.sort_order = next_sort_order(qs)
        if commit:
            obj.save()
        return obj


OptionItemFormSet = forms.inlineformset_factory(
    OptionSet,
    OptionItem,
    form=OptionItemForm,
    extra=2,
    can_delete=True,
)


class QuestionItemForm(forms.ModelForm):
    place_after = forms.ChoiceField(
        required=False,
        label="Place after",
        help_text="Choose the question that should sit immediately above this one. Leave as “At the end” to add it last.",
    )

    class Meta:
        model = QuestionItem
        fields = [
            "section",
            "label",
            "help_text",
            "input_type",
            "option_set",
            "is_required",
            "is_active",
        ]
        help_texts = {
            "section": "Which questionnaire section this question belongs to.",
            "input_type": "How the county answers: short text, long text, number, date, dropdown, and so on.",
            "option_set": "Required when the type is Dropdown list. Manage lists under Catalogues.",
            "is_required": "If ticked, the county cannot submit until this is answered. Every active question still counts toward the completion percentage.",
            "is_active": "Hidden questions are not shown to counties.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from collection.questionnaire_spec import SECTION_TITLES

        self.fields["section"] = forms.ChoiceField(
            choices=[(key, title) for key, title in SECTION_TITLES.items()],
            widget=forms.Select(attrs={"class": "input"}),
        )
        self.fields["option_set"].queryset = OptionSet.objects.order_by("name")
        self.fields["option_set"].required = False
        if self.instance.pk and self.instance.is_builtin:
            self.fields["section"].disabled = True
            self.fields["section"].help_text = "Built-in questions stay in their original section."
        section = self.instance.section if self.instance.pk else (self.initial.get("section") or "a")
        others = QuestionItem.objects.filter(section=section).order_by("sort_order", "label")
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        choices = [("", "At the end of the section"), ("start", "At the start of the section")]
        choices += [(str(item.pk), item.label) for item in others]
        self.fields["place_after"].choices = choices
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.is_builtin:
            cleaned["section"] = self.instance.section
        if cleaned.get("input_type") == QuestionItem.InputType.CHOICE and not cleaned.get("option_set"):
            self.add_error("option_set", "Choose a dropdown list for this question.")
        return cleaned

    def save(self, commit=True):
        item = super().save(commit=False)
        if not item.code:
            base = slugify(item.label)[:40] or "question"
            code = f"extra-{base}"
            suffix = 2
            while QuestionItem.objects.filter(code=code).exclude(pk=item.pk).exists():
                code = f"extra-{base}-{suffix}"
                suffix += 1
            item.code = code
        if not item.pk:
            item.is_builtin = False
        place = self.cleaned_data.get("place_after")
        qs = QuestionItem.objects.filter(section=item.section)
        if item.pk:
            qs = qs.exclude(pk=item.pk)
        if place == "start":
            first = qs.order_by("sort_order").first()
            item.sort_order = (first.sort_order - 10) if first else 10
        elif place:
            after = QuestionItem.objects.filter(pk=place).first()
            if after:
                nxt = qs.filter(sort_order__gt=after.sort_order).order_by("sort_order").first()
                if nxt:
                    item.sort_order = after.sort_order + max(1, (nxt.sort_order - after.sort_order) // 2)
                else:
                    item.sort_order = after.sort_order + 10
        elif not item.sort_order:
            item.sort_order = next_sort_order(qs)
        if commit:
            item.save()
            _resequence_questions(item.section)
            item.refresh_from_db()
        return item


def _resequence_questions(section):
    for index, question in enumerate(
        QuestionItem.objects.filter(section=section).order_by("sort_order", "id"), 1
    ):
        wanted = index * 10
        if question.sort_order != wanted:
            question.sort_order = wanted
            question.save(update_fields=["sort_order"])


