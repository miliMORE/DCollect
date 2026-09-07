from django.contrib import admin

from .models import (
    BenefitRow,
    CaseDocument,
    CaseDocumentFile,
    CaseEvent,
    CaseValidation,
    Clarification,
    ComparatorBenefitRow,
    ComparatorPayRow,
    CountyCase,
    IndividualResponse,
    JobPayRow,
    Questionnaire,
    StaffSurveyLink,
)


class JobPayInline(admin.TabularInline):
    model = JobPayRow
    extra = 0
    autocomplete_fields = ("job_group",)
    fields = (
        "job_group",
        "not_applicable",
        "src_equivalent",
        "min_basic",
        "max_basic",
        "house_allowance",
        "commuter_allowance",
        "airtime",
        "other_allowances",
    )


@admin.register(CountyCase)
class CountyCaseAdmin(admin.ModelAdmin):
    list_display = ("county", "survey_period", "status", "assigned_consultant", "updated_at")
    list_filter = ("status", "survey_period")
    search_fields = ("county__name",)
    autocomplete_fields = ("county", "survey_period", "assigned_consultant")


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("case", "department", "respondent_name", "updated_at")
    search_fields = ("case__county__name", "respondent_name")


@admin.register(JobPayRow)
class JobPayRowAdmin(admin.ModelAdmin):
    list_display = ("case", "job_group", "src_equivalent", "min_basic", "max_basic", "not_applicable")
    list_filter = ("not_applicable",)
    autocomplete_fields = ("job_group",)


@admin.register(BenefitRow)
class BenefitRowAdmin(admin.ModelAdmin):
    list_display = ("case", "benefit", "provided")


class CaseDocumentFileInline(admin.TabularInline):
    model = CaseDocumentFile
    extra = 0


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ("case", "document_type", "received", "uploaded_at")
    inlines = [CaseDocumentFileInline]


@admin.register(CaseDocumentFile)
class CaseDocumentFileAdmin(admin.ModelAdmin):
    list_display = ("document", "original_name", "uploaded_at", "uploaded_by")


@admin.register(CaseValidation)
class CaseValidationAdmin(admin.ModelAdmin):
    list_display = ("case", "item", "status")


@admin.register(Clarification)
class ClarificationAdmin(admin.ModelAdmin):
    list_display = ("case", "module", "resolved", "created_at")


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ("case", "verb", "actor", "created_at")
    readonly_fields = ("case", "actor", "verb", "detail", "created_at")


@admin.register(ComparatorPayRow)
class ComparatorPayRowAdmin(admin.ModelAdmin):
    list_display = ("organization", "survey_period", "job", "min_basic", "max_basic")


@admin.register(ComparatorBenefitRow)
class ComparatorBenefitRowAdmin(admin.ModelAdmin):
    list_display = ("organization", "survey_period", "benefit", "provided")


@admin.register(StaffSurveyLink)
class StaffSurveyLinkAdmin(admin.ModelAdmin):
    list_display = ("token", "county", "survey_period", "is_open", "is_active")
    list_filter = ("is_open", "is_active", "survey_period")


@admin.register(IndividualResponse)
class IndividualResponseAdmin(admin.ModelAdmin):
    list_display = ("county", "job_title", "current_basic", "submitted_at")
    list_filter = ("county", "survey_period", "employment_type")
    search_fields = ("job_title", "respondent_name", "county__name")
