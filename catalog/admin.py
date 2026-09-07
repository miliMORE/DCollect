from django.contrib import admin

from .models import (
    BenchmarkJob,
    BenefitType,
    ComparatorOrganization,
    County,
    DocumentType,
    JobFamily,
    JobGroup,
    OptionItem,
    OptionSet,
    QuestionItem,
    SRCGrade,
    SiteSettings,
    SurveyPeriod,
    ValidationItem,
)


class OptionItemInline(admin.TabularInline):
    model = OptionItem
    extra = 0


@admin.register(OptionSet)
class OptionSetAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    inlines = [OptionItemInline]
    search_fields = ("code", "name")


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "region", "is_active", "sort_order")
    list_filter = ("region", "is_active")
    search_fields = ("name", "code")


@admin.register(SurveyPeriod)
class SurveyPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(JobFamily)
class JobFamilyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "sort_order")


@admin.register(JobGroup)
class JobGroupAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "sort_order")
    search_fields = ("code", "name")


@admin.register(SRCGrade)
class SRCGradeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "sort_order")
    search_fields = ("code", "name")


@admin.register(BenchmarkJob)
class BenchmarkJobAdmin(admin.ModelAdmin):
    list_display = ("title", "job_family", "job_group", "src_grade", "is_required", "is_active")
    list_filter = ("job_family", "job_group", "is_active", "is_required")
    search_fields = ("title", "code")


@admin.register(BenefitType)
class BenefitTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_required", "collects_interest", "is_active", "sort_order")


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_required", "is_active", "sort_order")


@admin.register(ValidationItem)
class ValidationItemAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "sort_order")


@admin.register(ComparatorOrganization)
class ComparatorAdmin(admin.ModelAdmin):
    list_display = ("name", "sector", "include_in_market_median", "is_active", "sort_order")


@admin.register(QuestionItem)
class QuestionItemAdmin(admin.ModelAdmin):
    list_display = ("label", "section", "input_type", "is_required", "is_active", "is_builtin")
    list_filter = ("section", "is_required", "is_active", "is_builtin")
    search_fields = ("label", "code")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
