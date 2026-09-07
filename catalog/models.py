from django.db import models


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class County(Timestamped):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=80, unique=True)
    region = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Counties"

    def __str__(self):
        return self.name


class SurveyPeriod(Timestamped):
    name = models.CharField(max_length=120)
    code = models.SlugField(unique=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            SurveyPeriod.objects.exclude(pk=self.pk).update(is_active=False)


class OptionSet(Timestamped):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    help_text = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OptionItem(models.Model):
    option_set = models.ForeignKey(OptionSet, on_delete=models.CASCADE, related_name="items")
    value = models.CharField(max_length=80)
    label = models.CharField(max_length=160)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["option_set", "sort_order", "label"]
        unique_together = [("option_set", "value")]

    def __str__(self):
        return f"{self.option_set.code}: {self.label}"


class JobFamily(Timestamped):
    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Job families"

    def __str__(self):
        return self.name


class JobGroup(Timestamped):
    # County pay is collected for groups A–U, skipping I and O.
    PAY_CODES = tuple("ABCDEFGHJKLMNPQRSTU")

    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return self.code

    @property
    def title(self):
        return self.name or f"Job Group {self.code}"


class SRCGrade(Timestamped):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "code"]
        verbose_name = "SRC grade"

    def __str__(self):
        return self.code


class BenchmarkJob(Timestamped):
    title = models.CharField(max_length=160)
    code = models.SlugField(unique=True)
    job_family = models.ForeignKey(JobFamily, on_delete=models.PROTECT, related_name="jobs")
    job_group = models.ForeignKey(JobGroup, on_delete=models.PROTECT, related_name="jobs")
    src_grade = models.ForeignKey(
        SRCGrade, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs"
    )
    description = models.TextField(blank=True)
    is_required = models.BooleanField(
        default=True,
        help_text="If required, counties must complete or mark not applicable.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return f"{self.title} ({self.job_group.code})"


class BenefitType(Timestamped):
    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    collects_interest = models.BooleanField(default=False)
    is_required = models.BooleanField(
        default=True,
        help_text="If required, the county must mark whether the benefit is provided.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class DocumentType(Timestamped):
    name = models.CharField(max_length=160, unique=True)
    code = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ValidationItem(Timestamped):
    name = models.CharField(max_length=160, unique=True)
    code = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ComparatorOrganization(Timestamped):
    name = models.CharField(max_length=160, unique=True)
    code = models.SlugField(unique=True)
    sector = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    include_in_market_median = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class SiteSettings(Timestamped):
    org_name = models.CharField(max_length=160, default="BINSTOPEJ Management Solutions Ltd")
    client_name = models.CharField(
        max_length=200,
        default="County Public Service Board National Consultative Forum (CPSB-NCF)",
    )
    survey_title = models.CharField(
        max_length=200,
        default="County Public Service Salary & Remuneration Review",
    )
    short_name = models.CharField(max_length=40, default="DCollect")
    purpose_text = models.TextField(
        default=(
            "The County Public Service Board National Consultative Forum (CPSB-NCF) has engaged "
            "BINSTOPEJ Management Solutions Ltd to undertake a Salary and Benefits Survey covering "
            "Public Officers within the Executive County Public Service. The consultancy seeks to "
            "generate credible empirical evidence to guide remuneration reforms while promoting "
            "fairness, transparency, attraction and retention of competent public servants."
        )
    )
    how_to_use_text = models.TextField(
        default=(
            "Complete the institutional questionnaire, then provide benchmark-position and payroll "
            "information. Upload the supporting documents and use the validation checklist before "
            "certifying the county file for submission."
        )
    )
    confidentiality_text = models.TextField(
        default=(
            "Information provided will be treated as confidential and used solely for purposes of "
            "the Salary and Remuneration Review. Where institution-level data is commercially or "
            "administratively sensitive, aggregated information may be used for reporting."
        )
    )
    support_email = models.EmailField(blank=True, default="survey@binstopej.example")
    max_upload_mb = models.PositiveIntegerField(default=10)
    allow_county_see_analysis = models.BooleanField(default=False)
    require_certification_to_submit = models.BooleanField(default=True)
    require_complete_to_submit = models.BooleanField(
        default=True,
        help_text="County cannot submit until items marked required are complete. Overview percentages still count every active question, job group, benefit and document.",
    )
    jobs_require_src_equivalent = models.BooleanField(
        default=False,
        help_text="County must select an SRC equivalent for each applicable benchmark job.",
    )
    active_survey_period = models.ForeignKey(
        SurveyPeriod,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.short_name

    def save(self, *args, **kwargs):
        self.pk = 1
        name = (self.short_name or "").strip()
        if name.lower().replace(" ", "") in {"dcollects", "d-collects"}:
            name = "DCollect"
        self.short_name = name or "DCollect"
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class QuestionItem(Timestamped):
    class InputType(models.TextChoices):
        TEXT = "text", "Short text"
        TEXTAREA = "textarea", "Long text"
        INTEGER = "integer", "Whole number"
        DECIMAL = "decimal", "Decimal number"
        MONEY = "money", "Amount (KES)"
        PERCENT = "percent", "Percent"
        YEAR = "year", "Year"
        DATE = "date", "Date"
        EMAIL = "email", "Email"
        TEL = "tel", "Telephone"
        CHOICE = "choice", "Dropdown list"

    section = models.CharField(max_length=2, db_index=True)
    code = models.SlugField(unique=True, max_length=80)
    label = models.CharField(max_length=300)
    help_text = models.CharField(max_length=400, blank=True)
    input_type = models.CharField(max_length=20, choices=InputType.choices, default=InputType.TEXT)
    option_set = models.ForeignKey(
        OptionSet, null=True, blank=True, on_delete=models.SET_NULL, related_name="questions"
    )
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_builtin = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["section", "sort_order", "label"]

    def __str__(self):
        return self.label

    def section_title(self):
        from collection.questionnaire_spec import SECTION_TITLES

        return SECTION_TITLES.get(self.section, self.section.upper())
