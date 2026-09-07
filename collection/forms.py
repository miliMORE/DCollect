from decimal import Decimal

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

from catalog.models import BenchmarkJob, ComparatorOrganization, County, OptionSet, QuestionItem, SRCGrade, SiteSettings

from .questionnaire_spec import (
    CHOICE_SETS,
    GROUP_HEADINGS,
    HELP,
    INTEGER_FIELDS,
    LABELS,
    MONEY_FIELDS,
    PERCENT_FIELDS,
    SECTION_FIELDS,
)
from .models import (
    BenefitRow,
    CaseDocument,
    CaseValidation,
    Clarification,
    ComparatorBenefitRow,
    ComparatorPayRow,
    CountyCase,
    IndividualResponse,
    JobPayRow,
    Questionnaire,
)


def option_choices(code, include_blank=True, current=None):
    try:
        option_set = OptionSet.objects.prefetch_related("items").get(code=code)
        qs = option_set.items.filter(is_active=True)
        if not qs.exists():
            qs = option_set.items.all()
        items = [(i.value, i.label) for i in qs]
    except OptionSet.DoesNotExist:
        items = []
    values = {value for value, _label in items}
    if current not in (None, "") and current not in values:
        items.append((current, current))
    if include_blank:
        return [("", "— Select —")] + items
    return items


def style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
            field.widget.attrs.setdefault("class", "input")
        elif isinstance(field.widget, forms.Textarea):
            field.widget.attrs.setdefault("class", "input")
            field.widget.attrs.setdefault("rows", 3)
        elif isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "checkbox")
        else:
            field.widget.attrs.setdefault("class", "input")


def _field_for_question(item, required=False, current=None):
    label = item.label
    help_text = item.help_text
    attrs = {"class": "input"}
    if item.input_type == QuestionItem.InputType.TEXTAREA:
        field = forms.CharField(
            required=required, label=label, help_text=help_text, widget=forms.Textarea(attrs={**attrs, "rows": 3})
        )
    elif item.input_type == QuestionItem.InputType.INTEGER:
        field = forms.IntegerField(
            required=required, label=label, help_text=help_text, min_value=0, widget=forms.NumberInput(attrs={**attrs, "min": "0", "step": "1"})
        )
    elif item.input_type == QuestionItem.InputType.MONEY:
        field = forms.DecimalField(
            required=required, label=label, help_text=help_text, min_value=0, decimal_places=2, max_digits=16,
            widget=forms.NumberInput(attrs={**attrs, "min": "0", "step": "0.01", "inputmode": "decimal"}),
        )
    elif item.input_type == QuestionItem.InputType.PERCENT:
        field = forms.DecimalField(
            required=required, label=label, help_text=help_text, min_value=0, max_value=100, decimal_places=2, max_digits=6,
            widget=forms.NumberInput(attrs={**attrs, "min": "0", "max": "100", "step": "0.01"}),
        )
    elif item.input_type == QuestionItem.InputType.DECIMAL:
        field = forms.DecimalField(
            required=required, label=label, help_text=help_text, min_value=0, decimal_places=1, max_digits=8,
            widget=forms.NumberInput(attrs={**attrs, "min": "0", "step": "0.1"}),
        )
    elif item.input_type == QuestionItem.InputType.YEAR:
        field = forms.CharField(
            required=required, label=label, help_text=help_text, max_length=4,
            widget=forms.TextInput(attrs={**attrs, "inputmode": "numeric", "maxlength": "4", "placeholder": "YYYY"}),
        )
    elif item.input_type == QuestionItem.InputType.DATE:
        field = forms.DateField(
            required=required, label=label, help_text=help_text,
            widget=forms.DateInput(attrs={**attrs, "type": "date"}),
        )
    elif item.input_type == QuestionItem.InputType.EMAIL:
        field = forms.EmailField(required=required, label=label, help_text=help_text, widget=forms.EmailInput(attrs=attrs))
    elif item.input_type == QuestionItem.InputType.TEL:
        field = forms.CharField(required=required, label=label, help_text=help_text, widget=forms.TextInput(attrs={**attrs, "inputmode": "tel"}))
    elif item.input_type == QuestionItem.InputType.CHOICE:
        set_code = ""
        if item.option_set_id:
            set_code = item.option_set.code
        else:
            set_code = CHOICE_SETS.get(item.code, "")
        if set_code:
            choices = option_choices(set_code, current=current)
        else:
            choices = [("", "— Select —")]
            if current not in (None, ""):
                choices.append((current, current))
        if len(choices) <= 1:
            help_text = (help_text + " " if help_text else "") + (
                "This dropdown has no options yet. Under Setup → Catalogues → Dropdowns, "
                "add the list and attach it to this question."
            )
        field = forms.ChoiceField(required=required, label=label, help_text=help_text, choices=choices, widget=forms.Select(attrs=attrs))
    else:
        field = forms.CharField(required=required, label=label, help_text=help_text, widget=forms.TextInput(attrs=attrs))
    return field


class QuestionnaireForm(forms.ModelForm):
    class Meta:
        model = Questionnaire
        exclude = ["case", "updated_at"]

    def __init__(self, *args, section="a", **kwargs):
        self.section = section
        super().__init__(*args, **kwargs)
        self.questions = list(
            QuestionItem.objects.filter(section=section, is_active=True)
            .select_related("option_set")
            .order_by("sort_order", "label")
        )
        extras = {}
        if self.instance.pk:
            extras = {
                row.question_id: row.value
                for row in self.instance.extra_answers.all()
            }
        if self.questions:
            keep = {item.code for item in self.questions if item.is_builtin}
            for name in list(self.fields):
                if name not in keep:
                    self.fields.pop(name)
            ordered = {}
            for item in self.questions:
                if item.is_builtin:
                    if item.code not in self.fields and not hasattr(self.instance, item.code):
                        continue
                    current = getattr(self.instance, item.code, None)
                    field = _field_for_question(item, required=item.is_required, current=current)
                    field.initial = current
                    heading = GROUP_HEADINGS.get(item.code)
                    if heading:
                        field.group_heading = heading
                    ordered[item.code] = field
                else:
                    key = f"extra_{item.pk}"
                    current = extras.get(item.pk, "")
                    field = _field_for_question(item, required=item.is_required, current=current)
                    field.initial = current
                    heading = GROUP_HEADINGS.get(item.code)
                    if heading:
                        field.group_heading = heading
                    ordered[key] = field
            self.fields = ordered
        else:
            keep = SECTION_FIELDS.get(section, SECTION_FIELDS["a"])
            for name in list(self.fields):
                if name not in keep:
                    self.fields.pop(name)
            for field_name, set_code in CHOICE_SETS.items():
                if field_name in self.fields:
                    self.fields[field_name] = forms.ChoiceField(
                        choices=option_choices(
                            set_code, current=getattr(self.instance, field_name, None)
                        ),
                        required=False,
                        widget=forms.Select(attrs={"class": "input"}),
                    )
            for name, field in self.fields.items():
                field.label = LABELS.get(name, field.label)
                field.help_text = HELP.get(name, field.help_text)
                field.required = False
                heading = GROUP_HEADINGS.get(name)
                if heading:
                    field.group_heading = heading
                if name in INTEGER_FIELDS:
                    field.validators.append(MinValueValidator(0))
                    field.widget.attrs.update({"min": "0", "step": "1", "inputmode": "numeric"})
                elif name in MONEY_FIELDS:
                    field.validators.append(MinValueValidator(0))
                    field.widget.attrs.update({"min": "0", "step": "0.01", "inputmode": "decimal"})
                elif name in PERCENT_FIELDS:
                    field.validators.extend([MinValueValidator(0), MaxValueValidator(100)])
                    field.widget.attrs.update({"min": "0", "max": "100", "step": "0.01", "inputmode": "decimal"})
                elif name == "avg_years_in_grade":
                    field.validators.append(MinValueValidator(0))
                    field.widget.attrs.update({"min": "0", "step": "0.1", "inputmode": "decimal"})
                elif name == "last_review_year":
                    field.validators.append(
                        RegexValidator(r"^\d{4}$", "Enter a four-digit year, for example 2019.")
                    )
                    field.widget.attrs.update({"inputmode": "numeric", "maxlength": "4", "placeholder": "YYYY"})
                elif name == "respondent_email":
                    field.widget.attrs.update({"type": "email", "autocomplete": "email"})
                elif name == "respondent_telephone":
                    field.widget.attrs.update({"inputmode": "tel", "autocomplete": "tel"})
        style_fields(self)

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit:
            self._save_extras(obj)
        return obj

    def _save_extras(self, questionnaire):
        from .models import QuestionnaireAnswer

        for item in self.questions:
            if item.is_builtin:
                continue
            key = f"extra_{item.pk}"
            value = self.cleaned_data.get(key)
            if value is None:
                value = ""
            elif hasattr(value, "isoformat"):
                value = value.isoformat()
            else:
                value = str(value)
            QuestionnaireAnswer.objects.update_or_create(
                questionnaire=questionnaire,
                question=item,
                defaults={"value": value},
            )

    def clean_last_review_year(self):
        year = (self.cleaned_data.get("last_review_year") or "").strip()
        if not year:
            return year
        if not year.isdigit() or len(year) != 4:
            raise forms.ValidationError("Enter a four-digit year, for example 2019.")
        value = int(year)
        if value < 1990 or value > 2035:
            raise forms.ValidationError("Year must be between 1990 and 2035.")
        return year

    def clean_respondent_telephone(self):
        phone = (self.cleaned_data.get("respondent_telephone") or "").strip()
        if not phone:
            return phone
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 7:
            raise forms.ValidationError("Enter a telephone number with at least 7 digits.")
        return phone

    def clean(self):
        cleaned = super().clean()
        if "paid_above_maximum_why" in self.fields and cleaned.get("paid_above_maximum") == "Yes" and not (
            cleaned.get("paid_above_maximum_why") or ""
        ).strip():
            self.add_error("paid_above_maximum_why", "If Yes, say why employees are paid above maximum.")
        if "pay_difference_causes" in self.fields and cleaned.get("pay_differences") == "Yes" and not (
            cleaned.get("pay_difference_causes") or ""
        ).strip():
            self.add_error(
                "pay_difference_causes",
                "If Yes, state the causes of pay differentials.",
            )
        if "progression_factors_notes" in self.fields and cleaned.get("progression_factors") == "Other" and not (
            cleaned.get("progression_factors_notes") or ""
        ).strip():
            self.add_error("progression_factors_notes", "If Other, specify the factors.")
        if (
            "medical_cover_notes" in self.fields
            and (cleaned.get("medical_cover_how") or "") in {"Other", "Combination of arrangements"}
            and not (cleaned.get("medical_cover_notes") or "").strip()
        ):
            self.add_error(
                "medical_cover_notes",
                "Explain how medical insurance is handled for this county.",
            )
        if (
            "medical_cost_per_employee" in self.fields
            and cleaned.get("medical_insurance") in {"Yes", "Mixed"}
            and cleaned.get("medical_cost_per_employee") is None
        ):
            self.add_error(
                "medical_cost_per_employee",
                "If medical insurance is provided, enter the annual employer medical cost per employee (KES).",
            )
        parts = [cleaned.get("basic_pct"), cleaned.get("allowances_pct"), cleaned.get("other_cash_pct")]
        if all(part is not None for part in parts):
            total = sum(Decimal(part) for part in parts)
            if abs(total - Decimal("100")) > Decimal("1"):
                self.add_error(
                    "other_cash_pct",
                    f"Basic + allowances + other cash must add to 100%. Currently {total}%.",
                )
        return cleaned


class CertifyForm(forms.ModelForm):
    class Meta:
        model = CountyCase
        fields = ["certified_name", "certified_designation", "certified_initials"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        self.fields["certified_name"].label = "Name"
        self.fields["certified_designation"].label = "Designation"
        self.fields["certified_initials"].label = "Signature/Initials"
        self.fields["certified_name"].help_text = "SECTION K: RESPONDENT CERTIFICATION"
        self.fields["certified_designation"].help_text = "As on the Excel questionnaire."
        self.fields["certified_initials"].help_text = "Signature or initials. The date is recorded automatically."
        for name in self.fields:
            self.fields[name].required = True


class ClarificationForm(forms.ModelForm):
    class Meta:
        model = Clarification
        fields = ["module", "message"]
        widgets = {
            "module": forms.Select(
                choices=[
                    ("questionnaire", "Questionnaire"),
                    ("jobs", "Benchmark positions"),
                    ("benefits", "Benefits"),
                    ("documents", "Documents"),
                    ("general", "General"),
                ]
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        self.fields["message"].required = True


class ClarificationResponseForm(forms.Form):
    response = forms.CharField(widget=forms.Textarea(attrs={"class": "input", "rows": 3}))


class CaseAssignForm(forms.ModelForm):
    class Meta:
        model = CountyCase
        fields = ["assigned_consultant", "status", "internal_notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User

        self.fields["assigned_consultant"].queryset = User.objects.filter(
            role__in=[User.Role.CONSULTANT, User.Role.ADMIN], is_active=True
        )
        self.fields["assigned_consultant"].required = False
        style_fields(self)


class JobPayForm(forms.ModelForm):
    class Meta:
        model = JobPayRow
        fields = [
            "not_applicable",
            "src_equivalent",
            "min_basic",
            "max_basic",
            "house_allowance",
            "commuter_allowance",
            "airtime",
            "other_allowances",
        ]

    def __init__(self, *args, src_grades=None, require_src=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["src_equivalent"] = forms.CharField(
            required=False,
            label="SRC equivalent",
            max_length=40,
            widget=forms.TextInput(attrs={"class": "input src-eq", "placeholder": "e.g. EX4"}),
        )
        style_fields(self)
        self.fields["src_equivalent"].widget.attrs["class"] = "input src-eq"
        if require_src is None:
            require_src = SiteSettings.load().jobs_require_src_equivalent
        self.require_src = require_src
        for name in (
            "min_basic",
            "max_basic",
            "house_allowance",
            "commuter_allowance",
            "airtime",
            "other_allowances",
        ):
            self.fields[name].widget.attrs.setdefault("inputmode", "decimal")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("not_applicable"):
            return cleaned
        minimum = cleaned.get("min_basic")
        maximum = cleaned.get("max_basic")
        if minimum is not None and maximum is not None and maximum < minimum:
            self.add_error("max_basic", "Maximum cannot be below minimum.")
        if getattr(self, "require_src", False) and not cleaned.get("src_equivalent"):
            self.add_error("src_equivalent", "Enter the SRC equivalent for this job group.")
        return cleaned


class BenefitForm(forms.ModelForm):
    class Meta:
        model = BenefitRow
        fields = [
            "provided",
            "interest_charged",
            "employer_contribution",
            "employee_contribution",
            "eligibility",
            "comments",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["provided"] = forms.ChoiceField(
            choices=option_choices("provided", current=self.instance.provided),
            required=False,
            widget=forms.Select(attrs={"class": "input"}),
        )
        self.show_interest = bool(
            self.instance.benefit_id and self.instance.benefit.collects_interest
        )
        self.fields["interest_charged"] = forms.ChoiceField(
            choices=option_choices("yes_no", current=self.instance.interest_charged),
            required=False,
            widget=forms.Select(attrs={"class": "input"}),
        )
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        provided = (cleaned.get("provided") or "").strip()
        if (
            getattr(self, "show_interest", False)
            and provided.lower() in {"yes", "partial"}
            and not (cleaned.get("interest_charged") or "").strip()
        ):
            self.add_error("interest_charged", "Say whether interest is charged.")
        return cleaned


class ValidationForm(forms.ModelForm):
    class Meta:
        model = CaseValidation
        fields = ["status", "comments"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"] = forms.ChoiceField(
            choices=option_choices("validation_status", current=self.instance.status),
            required=False,
            widget=forms.Select(attrs={"class": "input"}),
        )
        style_fields(self)


class DocumentMetaForm(forms.ModelForm):
    class Meta:
        model = CaseDocument
        fields = ["received", "comments", "not_available"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["received"] = forms.ChoiceField(
            choices=option_choices("provided", current=self.instance.received),
            required=False,
            widget=forms.Select(attrs={"class": "input"}),
        )
        required_doc = bool(self.instance.document_type_id and self.instance.document_type.is_required)
        if required_doc:
            self.fields.pop("not_available", None)
        else:
            self.fields["not_available"].label = "Not available"
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        if self.instance.document_type_id and self.instance.document_type.is_required:
            cleaned["not_available"] = False
        received = (cleaned.get("received") or "").strip()
        if received.lower() in {"yes", "partial"} and not self.instance.has_files() and not cleaned.get(
            "not_available"
        ):
            self.add_error("received", "Upload a file before marking this as received.")
        return cleaned


class UploadForm(forms.Form):
    file = forms.FileField()


class ComparatorPayForm(forms.ModelForm):
    class Meta:
        model = ComparatorPayRow
        fields = [
            "not_applicable",
            "min_basic",
            "max_basic",
            "median_basic",
            "house_allowance",
            "commuter_allowance",
            "airtime",
            "other_allowances",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        for name in (
            "min_basic",
            "max_basic",
            "median_basic",
            "house_allowance",
            "commuter_allowance",
            "airtime",
            "other_allowances",
        ):
            self.fields[name].widget.attrs.setdefault("inputmode", "decimal")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("not_applicable"):
            return cleaned
        minimum = cleaned.get("min_basic")
        maximum = cleaned.get("max_basic")
        if minimum is not None and maximum is not None and maximum < minimum:
            self.add_error("max_basic", "Maximum cannot be below minimum.")
        return cleaned


class ComparatorBenefitForm(forms.ModelForm):
    class Meta:
        model = ComparatorBenefitRow
        fields = [
            "provided",
            "interest_charged",
            "employer_contribution",
            "employee_contribution",
            "eligibility",
            "comments",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["provided"] = forms.ChoiceField(
            choices=option_choices("provided", current=self.instance.provided),
            required=False,
            widget=forms.Select(attrs={"class": "input"}),
        )
        style_fields(self)


class ComparatorOrgForm(forms.ModelForm):
    class Meta:
        model = ComparatorOrganization
        fields = ["name", "code", "sector", "include_in_market_median", "is_active", "notes"]
        help_texts = {
            "code": "Short slug used internally, for example src-public-service. Leave blank to generate from the name.",
            "include_in_market_median": "If ticked, this organisation’s medians enter the market median on Analysis and reports.",
            "sector": "For example National government, State corporation, Peer county.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["code"].required = False
        style_fields(self)

    def clean_code(self):
        from django.utils.text import slugify

        code = self.cleaned_data.get("code")
        if not code:
            code = slugify(self.cleaned_data.get("name") or "")[:50]
        return code

    def save(self, commit=True):
        from catalog.ordering import next_sort_order

        org = super().save(commit=False)
        if not org.pk and not org.sort_order:
            org.sort_order = next_sort_order(ComparatorOrganization.objects.all())
        if commit:
            org.save()
        return org


JobPayFormSet = forms.inlineformset_factory(
    CountyCase, JobPayRow, form=JobPayForm, extra=0, can_delete=False
)
BenefitFormSet = forms.inlineformset_factory(
    CountyCase, BenefitRow, form=BenefitForm, extra=0, can_delete=False
)
ValidationFormSet = forms.inlineformset_factory(
    CountyCase, CaseValidation, form=ValidationForm, extra=0, can_delete=False
)


class IndividualResponseForm(forms.ModelForm):
    class Meta:
        model = IndividualResponse
        fields = [
            "county",
            "job",
            "job_title",
            "department",
            "employment_type",
            "years_in_role",
            "current_basic",
            "house_allowance",
            "commuter_allowance",
            "airtime",
            "other_allowances",
            "respondent_name",
            "respondent_email",
            "notes",
        ]
        labels = {
            "county": "County Government you work for",
            "job": "Benchmark position this work is closest to",
            "job_title": "Your job title",
            "department": "Department / directorate / unit",
            "employment_type": "Terms of service",
            "years_in_role": "Years in this role",
            "current_basic": "Current basic salary (KES, monthly)",
            "house_allowance": "House allowance (KES, monthly)",
            "commuter_allowance": "Commuter allowance (KES, monthly)",
            "airtime": "Airtime / communication allowance (KES, monthly)",
            "other_allowances": "Other cash allowances (KES, monthly)",
            "respondent_name": "Your name (optional, kept confidential)",
            "respondent_email": "Email (optional, if we need to follow up)",
            "notes": "Anything else about this post",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, locked_county=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.locked_county = locked_county
        self.fields["job"].queryset = BenchmarkJob.objects.filter(is_active=True).order_by(
            "sort_order", "title"
        )
        self.fields["job"].required = False
        self.fields["job"].empty_label = "— Other / not on the list —"
        self.fields["county"].queryset = County.objects.filter(is_active=True)
        self.fields["current_basic"].required = True
        self.fields["job_title"].required = False
        if locked_county is not None:
            self.fields["county"].initial = locked_county
            self.fields["county"].disabled = True
            self.fields["county"].required = False
        for name in (
            "current_basic",
            "house_allowance",
            "commuter_allowance",
            "airtime",
            "other_allowances",
            "years_in_role",
        ):
            self.fields[name].widget.attrs.setdefault("inputmode", "decimal")
            self.fields[name].widget.attrs.setdefault("min", "0")
        style_fields(self)

    def clean_current_basic(self):
        value = self.cleaned_data.get("current_basic")
        if value is None:
            raise forms.ValidationError("Enter your current basic salary.")
        if value < 0:
            raise forms.ValidationError("Salary cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()
        if self.locked_county is not None:
            cleaned["county"] = self.locked_county
        elif not cleaned.get("county"):
            self.add_error("county", "Select the county you work for.")
        job = cleaned.get("job")
        title = (cleaned.get("job_title") or "").strip()
        if job and not title:
            cleaned["job_title"] = job.title
        elif not job and not title:
            self.add_error("job_title", "Enter your job title, or pick the closest benchmark position.")
        return cleaned
