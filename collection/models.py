from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from catalog.models import (
    BenchmarkJob,
    BenefitType,
    ComparatorOrganization,
    County,
    DocumentType,
    JobGroup,
    SRCGrade,
    SurveyPeriod,
    ValidationItem,
)


class CountyCase(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        CLARIFICATION = "clarification", "Clarification requested"
        VALIDATED = "validated", "Validated"
        IN_ANALYSIS = "in_analysis", "In analysis"
        CLOSED = "closed", "Closed"

    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name="cases")
    survey_period = models.ForeignKey(SurveyPeriod, on_delete=models.CASCADE, related_name="cases")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    assigned_consultant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_cases",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    certified_at = models.DateTimeField(null=True, blank=True)
    certified_name = models.CharField(max_length=160, blank=True)
    certified_designation = models.CharField(max_length=160, blank=True)
    certified_initials = models.CharField(max_length=40, blank=True)
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("county", "survey_period")]
        ordering = ["county__name"]

    def __str__(self):
        return f"{self.county.name} — {self.survey_period.name}"

    @property
    def is_locked_for_county(self):
        return self.status in {
            self.Status.SUBMITTED,
            self.Status.VALIDATED,
            self.Status.IN_ANALYSIS,
            self.Status.CLOSED,
        }

    def unlocked_modules_for_county(self):
        all_modules = {"questionnaire", "jobs", "benefits", "documents", "certify"}
        if self.status == self.Status.DRAFT:
            return all_modules
        if self.status == self.Status.CLARIFICATION:
            open_mods = set(
                self.clarifications.filter(resolved=False).values_list("module", flat=True)
            )
            if not open_mods or "general" in open_mods:
                return all_modules
            allowed = {m for m in open_mods if m in {"questionnaire", "jobs", "benefits", "documents"}}
            if allowed:
                allowed.add("certify")
            return allowed
        return set()

    def mark_submitted(self, user):
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.submitted_by = user
        self.save()

    def request_clarification(self):
        self.status = self.Status.CLARIFICATION
        self.save(update_fields=["status", "updated_at"])

    def mark_validated(self, user):
        self.status = self.Status.VALIDATED
        self.validated_at = timezone.now()
        self.validated_by = user
        self.save()

    def get_questionnaire(self):
        try:
            return self.questionnaire
        except ObjectDoesNotExist:
            return None

    def progress(self):
        from catalog.models import SiteSettings

        q = self.get_questionnaire()
        q_score = q.completion_ratio() if q else 0
        q_required = q.required_completion_ratio() if q else 0
        require_src = SiteSettings.load().jobs_require_src_equivalent
        job_rows = list(
            self.job_rows.select_related("job_group").filter(job_group__code__in=JobGroup.PAY_CODES)
        )
        jobs = len(job_rows)
        jobs_done = sum(1 for row in job_rows if row.collection_complete(require_src=require_src))
        job_score = (jobs_done / jobs) if jobs else 0
        benefit_rows = [
            r
            for r in self.benefit_rows.select_related("benefit")
            if r.benefit.is_active
        ]
        benefits_done = sum(1 for r in benefit_rows if r.collection_complete())
        benefit_score = (benefits_done / len(benefit_rows)) if benefit_rows else 0
        required_benefits = [r for r in benefit_rows if r.benefit.is_required]
        if required_benefits:
            benefit_required = sum(
                1 for r in required_benefits if r.collection_complete()
            ) / len(required_benefits)
        else:
            benefit_required = 1
        docs = list(
            self.documents.filter(document_type__is_active=True)
            .select_related("document_type")
            .prefetch_related("attachments")
        )
        docs_done = sum(1 for doc in docs if doc.slot_complete())
        doc_score = (docs_done / len(docs)) if docs else 0
        required_docs = [doc for doc in docs if doc.document_type.is_required]
        if required_docs:
            doc_required = sum(1 for doc in required_docs if doc.has_files()) / len(required_docs)
        else:
            doc_required = 1
        val_rows = [
            row
            for row in self.validations.select_related("item")
            if row.item.is_active
        ]
        val_done = sum(1 for row in val_rows if (row.status or "").strip())
        val_score = (val_done / len(val_rows)) if val_rows else 0
        cert = 1 if self.certified_at else 0
        overall = (q_score * 0.35) + (job_score * 0.25) + (benefit_score * 0.15) + (doc_score * 0.15) + (cert * 0.10)
        return {
            "questionnaire": round(q_score * 100),
            "jobs": round(job_score * 100),
            "benefits": round(benefit_score * 100),
            "documents": round(doc_score * 100),
            "validation": round(val_score * 100),
            "validation_total": len(val_rows),
            "certified": bool(self.certified_at),
            "overall": round(overall * 100),
            "required": {
                "questionnaire": round(q_required * 100),
                "jobs": round(job_score * 100),
                "benefits": round(benefit_required * 100),
                "documents": round(doc_required * 100),
            },
        }

    def validation_complete(self):
        progress = self.progress()
        if not progress["validation_total"]:
            return True
        return progress["validation"] == 100


class Questionnaire(models.Model):
    case = models.OneToOneField(CountyCase, on_delete=models.CASCADE, related_name="questionnaire")

    # A
    department = models.CharField(max_length=200, blank=True)
    respondent_name = models.CharField(max_length=160, blank=True)
    respondent_designation = models.CharField(max_length=160, blank=True)
    respondent_telephone = models.CharField(max_length=40, blank=True)
    respondent_email = models.EmailField(blank=True)

    # B
    permanent_pensionable = models.PositiveIntegerField(null=True, blank=True)
    contract_employees = models.PositiveIntegerField(null=True, blank=True)
    temporary_casual = models.PositiveIntegerField(null=True, blank=True)
    other_employees = models.PositiveIntegerField(null=True, blank=True)

    # C
    approved_policy = models.CharField(max_length=80, blank=True)
    philosophy_defined = models.CharField(max_length=40, blank=True)
    market_position = models.CharField(max_length=80, blank=True)
    last_review_year = models.CharField(max_length=10, blank=True)
    review_triggers = models.TextField(blank=True)

    # D
    number_of_grades = models.PositiveIntegerField(null=True, blank=True)
    progression_factors = models.CharField(max_length=80, blank=True)
    progression_factors_notes = models.TextField(blank=True)
    paid_above_maximum = models.CharField(max_length=40, blank=True)
    paid_above_maximum_why = models.TextField(blank=True)

    # E
    main_allowances = models.TextField(blank=True)
    remunerative_allowances = models.TextField(blank=True)
    non_remunerative_allowances = models.TextField(blank=True)
    annual_allowance_expenditure = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    medical_insurance = models.CharField(max_length=120, blank=True)
    medical_cover_how = models.CharField(max_length=160, blank=True)
    medical_cover_notes = models.TextField(blank=True)
    medical_cost_per_employee = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    pension_employer_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    pension_employee_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    gratuity_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    other_significant_benefits = models.TextField(blank=True)

    # F
    recruitment_challenges = models.TextField(blank=True)
    job_families_recruitment = models.TextField(blank=True)
    job_families_retention = models.TextField(blank=True)
    challenge_reasons = models.TextField(blank=True)
    retention_challenge_reasons = models.TextField(blank=True)
    benchmarking_frequency = models.CharField(max_length=40, blank=True)
    usual_comparators = models.TextField(blank=True)

    # G
    internal_equity = models.CharField(max_length=80, blank=True)
    pay_differences = models.CharField(max_length=40, blank=True)
    pay_difference_causes = models.TextField(blank=True)
    compression_concern = models.CharField(max_length=40, blank=True)
    compression_grades = models.CharField(max_length=200, blank=True)
    basic_vs_market = models.CharField(max_length=80, blank=True)
    benefits_vs_market = models.CharField(max_length=80, blank=True)
    categories_below_market = models.TextField(blank=True)
    categories_above_market = models.TextField(blank=True)

    # H
    basic_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    allowances_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    other_cash_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    progression_method = models.CharField(max_length=80, blank=True)
    avg_years_in_grade = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    placement_factors = models.TextField(blank=True)

    # I
    personnel_pct_budget = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    can_accommodate_increase = models.CharField(max_length=80, blank=True)
    implementation_approach = models.CharField(max_length=80, blank=True)
    implementation_period = models.CharField(max_length=40, blank=True)
    priority_categories = models.TextField(blank=True)

    # J documents & observations
    salary_structure_attached = models.CharField(max_length=40, blank=True)
    payroll_extract_attached = models.CharField(max_length=40, blank=True)
    allowance_schedule_attached = models.CharField(max_length=40, blank=True)
    benefits_schedule_attached = models.CharField(max_length=40, blank=True)
    hr_policy_attached = models.CharField(max_length=40, blank=True)
    previous_survey_attached = models.CharField(max_length=40, blank=True)
    three_challenges = models.TextField(blank=True)
    three_recommendations = models.TextField(blank=True)
    other_comments = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def total_employees(self):
        parts = [
            self.permanent_pensionable,
            self.contract_employees,
            self.temporary_casual,
            self.other_employees,
        ]
        if all(p is None for p in parts):
            return None
        return sum(p or 0 for p in parts)

    SECTION_FIELDS = {
        "a": ["department", "respondent_name", "respondent_designation", "respondent_telephone", "respondent_email"],
        "b": ["permanent_pensionable", "contract_employees", "temporary_casual", "other_employees"],
        "c": ["approved_policy", "philosophy_defined", "market_position", "last_review_year", "review_triggers"],
        "d": ["number_of_grades", "progression_factors", "paid_above_maximum"],
        "e": [
            "remunerative_allowances",
            "non_remunerative_allowances",
            "annual_allowance_expenditure",
            "medical_insurance",
            "medical_cover_how",
            "pension_employer_pct",
            "gratuity_pct",
        ],
        "f": [
            "recruitment_challenges",
            "job_families_recruitment",
            "job_families_retention",
            "challenge_reasons",
            "retention_challenge_reasons",
            "benchmarking_frequency",
        ],
        "g": ["internal_equity", "pay_differences"],
        "h": ["basic_pct", "allowances_pct", "progression_method", "placement_factors"],
        "i": ["personnel_pct_budget", "can_accommodate_increase", "implementation_approach", "implementation_period"],
        "j": [
            "salary_structure_attached",
            "allowance_schedule_attached",
            "benefits_schedule_attached",
            "previous_survey_attached",
            "three_challenges",
            "three_recommendations",
        ],
    }

    FOLLOW_UP_WHEN = {
        "progression_factors_notes": ("progression_factors", ("Other",)),
        "paid_above_maximum_why": ("paid_above_maximum", ("Yes",)),
        "pay_difference_causes": ("pay_differences", ("Yes",)),
        "medical_cover_notes": ("medical_cover_how", ("Other", "Combination of arrangements")),
        "medical_cost_per_employee": ("medical_insurance", ("Yes", "Mixed")),
    }

    @staticmethod
    def _is_filled(value):
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def _answer_map(self):
        if not hasattr(self, "_answer_cache"):
            if self.pk:
                self._answer_cache = {
                    row.question_id: row.value for row in self.extra_answers.all()
                }
            else:
                self._answer_cache = {}
        return self._answer_cache

    def _answer_value(self, item):
        if item.is_builtin and hasattr(self, item.code):
            return getattr(self, item.code)
        return self._answer_map().get(item.id, "")

    def _question_applies(self, item):
        rule = self.FOLLOW_UP_WHEN.get(getattr(item, "code", item))
        if not rule:
            return True
        parent, expected = rule
        value = getattr(self, parent, None)
        if isinstance(value, str):
            value = value.strip()
        return value in expected

    def _questions_for_section(self, key):
        from catalog.models import QuestionItem

        if not hasattr(self, "_questions_by_section"):
            grouped = {}
            for item in QuestionItem.objects.filter(is_active=True):
                grouped.setdefault(item.section, []).append(item)
            self._questions_by_section = grouped
        return list(self._questions_by_section.get(key, []))

    def section_stats(self, key):
        items = self._questions_for_section(key)
        if items:
            applicable = [item for item in items if self._question_applies(item)]
            done = sum(1 for item in applicable if self._is_filled(self._answer_value(item)))
            return done, len(applicable)
        fields = [
            name
            for name in self.SECTION_FIELDS.get(key, [])
            if self._question_applies(name)
        ]
        done = sum(1 for name in fields if self._is_filled(getattr(self, name, None)))
        return done, len(fields)

    def section_complete(self, key):
        done, total = self.section_stats(key)
        return total > 0 and done == total

    def completion_ratio(self):
        done = total = 0
        for key in self.SECTION_FIELDS:
            section_done, section_total = self.section_stats(key)
            done += section_done
            total += section_total
        if not total:
            return 0
        return done / total

    def required_completion_ratio(self):
        done = total = 0
        for key in self.SECTION_FIELDS:
            items = [item for item in self._questions_for_section(key) if self._question_applies(item)]
            required = [item for item in items if item.is_required]
            if required:
                total += len(required)
                done += sum(1 for item in required if self._is_filled(self._answer_value(item)))
            elif not items:
                fields = [
                    name
                    for name in self.SECTION_FIELDS.get(key, [])
                    if self._question_applies(name)
                ]
                total += len(fields)
                done += sum(1 for name in fields if self._is_filled(getattr(self, name, None)))
        if not total:
            return 1
        return done / total


class QuestionnaireAnswer(models.Model):
    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name="extra_answers"
    )
    question = models.ForeignKey(
        "catalog.QuestionItem", on_delete=models.CASCADE, related_name="answers"
    )
    value = models.TextField(blank=True)

    class Meta:
        unique_together = [("questionnaire", "question")]


class JobPayRow(models.Model):
    case = models.ForeignKey(CountyCase, on_delete=models.CASCADE, related_name="job_rows")
    job_group = models.ForeignKey(JobGroup, on_delete=models.CASCADE, related_name="county_pay_rows")
    not_applicable = models.BooleanField(default=False)
    src_equivalent = models.CharField(
        max_length=40,
        blank=True,
        help_text="SRC denotation for this job group as used by the county, for example EX4.",
    )
    min_basic = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_basic = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    median_basic = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Legacy field. Analysis uses the midpoint of min and max; this is only a fallback if both are blank.",
    )
    house_allowance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    commuter_allowance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    airtime = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    other_allowances = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    headcount = models.PositiveIntegerField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("case", "job_group")]
        ordering = ["job_group__sort_order", "job_group__code"]

    def __str__(self):
        return f"{self.case.county.name} / Job Group {self.job_group.code}"

    def src_equivalent_code(self):
        return (self.src_equivalent or "").strip()

    def midpoint_basic(self):
        if self.min_basic is not None and self.max_basic is not None:
            return (self.min_basic + self.max_basic) / Decimal("2")
        if self.min_basic is not None:
            return self.min_basic
        if self.max_basic is not None:
            return self.max_basic
        return self.median_basic

    def collection_complete(self, require_src=False):
        if self.not_applicable:
            return True
        if self.min_basic is None or self.max_basic is None:
            return False
        if require_src and not (self.src_equivalent or "").strip():
            return False
        return True

    def total_cash(self):
        base = self.midpoint_basic()
        if base is None and not any(
            [self.house_allowance, self.commuter_allowance, self.airtime, self.other_allowances]
        ):
            return None
        total = base or Decimal("0")
        for part in (self.house_allowance, self.commuter_allowance, self.airtime, self.other_allowances):
            if part:
                total += part
        return total


class BenefitRow(models.Model):
    case = models.ForeignKey(CountyCase, on_delete=models.CASCADE, related_name="benefit_rows")
    benefit = models.ForeignKey(BenefitType, on_delete=models.CASCADE, related_name="county_rows")
    provided = models.CharField(max_length=20, blank=True)
    interest_charged = models.CharField(max_length=80, blank=True)
    employer_contribution = models.CharField(max_length=120, blank=True)
    employee_contribution = models.CharField(max_length=120, blank=True)
    eligibility = models.CharField(max_length=200, blank=True)
    comments = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("case", "benefit")]
        ordering = ["benefit__sort_order"]

    def collection_complete(self):
        provided = (self.provided or "").strip()
        if not provided:
            return False
        if (
            self.benefit_id
            and self.benefit.collects_interest
            and provided.lower() in {"yes", "partial"}
            and not (self.interest_charged or "").strip()
        ):
            return False
        return True


class CaseDocument(models.Model):
    case = models.ForeignKey(CountyCase, on_delete=models.CASCADE, related_name="documents")
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name="slots")
    file = models.FileField(upload_to="cases/%Y/%m/", blank=True)
    not_available = models.BooleanField(
        default=False,
        help_text="Allowed only when the document type is optional.",
    )
    received = models.CharField(max_length=20, blank=True)
    comments = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = [("case", "document_type")]
        ordering = ["document_type__sort_order"]

    def all_files(self):
        files = list(self.attachments.all())
        if self.file:
            files.append(self)
        return files

    def file_names(self):
        names = [att.display_name() for att in self.attachments.all()]
        if self.file:
            names.append(Path(self.file.name).name)
        return names

    def file_count(self):
        n = self.attachments.count()
        if self.file:
            n += 1
        return n

    def has_files(self):
        if self.file:
            return True
        cache = getattr(self, "_prefetched_objects_cache", None) or {}
        if "attachments" in cache:
            return bool(cache["attachments"])
        return self.attachments.exists()

    def slot_complete(self):
        if self.has_files():
            return True
        if self.not_available and not self.document_type.is_required:
            return True
        return False

    def status_label(self):
        if self.has_files():
            return self.received or "Yes"
        if self.not_available:
            return "Not available"
        return "No"


class CaseDocumentFile(models.Model):
    document = models.ForeignKey(CaseDocument, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="cases/%Y/%m/")
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["uploaded_at", "id"]

    def display_name(self):
        if self.original_name:
            return self.original_name
        return Path(self.file.name).name if self.file else "file"


class CaseValidation(models.Model):
    case = models.ForeignKey(CountyCase, on_delete=models.CASCADE, related_name="validations")
    item = models.ForeignKey(ValidationItem, on_delete=models.CASCADE, related_name="rows")
    status = models.CharField(max_length=40, blank=True)
    comments = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("case", "item")]
        ordering = ["item__sort_order"]


class Clarification(models.Model):
    case = models.ForeignKey(CountyCase, on_delete=models.CASCADE, related_name="clarifications")
    module = models.CharField(max_length=40)
    message = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    response = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class CaseEvent(models.Model):
    case = models.ForeignKey(CountyCase, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    verb = models.CharField(max_length=80)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ComparatorPayRow(models.Model):
    organization = models.ForeignKey(
        ComparatorOrganization, on_delete=models.CASCADE, related_name="pay_rows"
    )
    survey_period = models.ForeignKey(SurveyPeriod, on_delete=models.CASCADE, related_name="comparator_rows")
    job = models.ForeignKey(BenchmarkJob, on_delete=models.CASCADE, related_name="comparator_rows")
    not_applicable = models.BooleanField(default=False)
    min_basic = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_basic = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    median_basic = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    house_allowance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    commuter_allowance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    airtime = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    other_allowances = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("organization", "survey_period", "job")]
        ordering = ["job__sort_order"]

    def midpoint_basic(self):
        if self.median_basic is not None:
            return self.median_basic
        if self.min_basic is not None and self.max_basic is not None:
            return (self.min_basic + self.max_basic) / Decimal("2")
        return self.min_basic or self.max_basic

    def total_cash(self):
        base = self.midpoint_basic()
        if base is None:
            extras = [self.house_allowance, self.commuter_allowance, self.airtime, self.other_allowances]
            if not any(extras):
                return None
            base = Decimal("0")
        total = base
        for part in (self.house_allowance, self.commuter_allowance, self.airtime, self.other_allowances):
            if part:
                total += part
        return total


class ComparatorBenefitRow(models.Model):
    organization = models.ForeignKey(
        ComparatorOrganization, on_delete=models.CASCADE, related_name="benefit_rows"
    )
    survey_period = models.ForeignKey(SurveyPeriod, on_delete=models.CASCADE, related_name="comparator_benefits")
    benefit = models.ForeignKey(BenefitType, on_delete=models.CASCADE, related_name="comparator_rows")
    provided = models.CharField(max_length=20, blank=True)
    interest_charged = models.CharField(max_length=80, blank=True)
    employer_contribution = models.CharField(max_length=120, blank=True)
    employee_contribution = models.CharField(max_length=120, blank=True)
    eligibility = models.CharField(max_length=200, blank=True)
    comments = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("organization", "survey_period", "benefit")]
        ordering = ["benefit__sort_order"]


class StaffSurveyLink(models.Model):

    token = models.CharField(max_length=64, unique=True, db_index=True)
    county = models.ForeignKey(
        County,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="staff_survey_links",
        help_text="If set, every response is stored against this county. If blank, the person chooses a county.",
    )
    survey_period = models.ForeignKey(
        SurveyPeriod, on_delete=models.CASCADE, related_name="staff_survey_links"
    )
    is_open = models.BooleanField(
        default=False,
        help_text="Open links let the respondent pick the county. County links are locked to one county.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["county__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["survey_period", "county"],
                condition=Q(is_open=False, county__isnull=False),
                name="unique_county_staff_link",
            ),
            models.UniqueConstraint(
                fields=["survey_period"],
                condition=Q(is_open=True),
                name="unique_open_staff_link",
            ),
        ]

    def __str__(self):
        if self.is_open:
            return f"Open staff survey · {self.survey_period}"
        if self.county_id:
            return f"{self.county.name} staff survey · {self.survey_period}"
        return self.token


class IndividualResponse(models.Model):
    class EmploymentType(models.TextChoices):
        PERMANENT = "permanent", "Permanent & pensionable"
        CONTRACT = "contract", "Contract"
        CASUAL = "casual", "Temporary / casual"
        OTHER = "other", "Other"

    link = models.ForeignKey(
        StaffSurveyLink, on_delete=models.SET_NULL, null=True, blank=True, related_name="responses"
    )
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name="individual_responses")
    survey_period = models.ForeignKey(
        SurveyPeriod, on_delete=models.CASCADE, related_name="individual_responses"
    )
    job = models.ForeignKey(
        BenchmarkJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="individual_responses",
    )
    job_title = models.CharField(max_length=160)
    department = models.CharField(max_length=200, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, blank=True
    )
    years_in_role = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    current_basic = models.DecimalField(max_digits=14, decimal_places=2)
    house_allowance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    commuter_allowance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    airtime = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    other_allowances = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    respondent_name = models.CharField(max_length=160, blank=True)
    respondent_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.county.name} · {self.job_title}"

    def total_cash(self):
        total = self.current_basic or Decimal("0")
        for part in (self.house_allowance, self.commuter_allowance, self.airtime, self.other_allowances):
            if part:
                total += part
        return total


def log_event(case, user, verb, detail=""):
    CaseEvent.objects.create(case=case, actor=user, verb=verb, detail=detail)
