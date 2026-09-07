from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditEntry, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "county", "is_active", "must_change_password")
    list_filter = ("role", "is_active", "must_change_password", "county")
    search_fields = ("username", "first_name", "last_name", "email")
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "DCollect",
            {"fields": ("role", "county", "phone", "job_title", "must_change_password")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "DCollect",
            {"fields": ("role", "county", "phone", "job_title", "must_change_password")},
        ),
    )


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_username", "actor_role", "summary", "category", "outcome", "ip_address")
    list_filter = ("category", "outcome", "actor_role")
    search_fields = ("summary", "detail", "actor_username", "actor_name", "target_label", "path")
    readonly_fields = (
        "created_at",
        "actor",
        "actor_username",
        "actor_name",
        "actor_role",
        "category",
        "action",
        "summary",
        "detail",
        "outcome",
        "county",
        "case",
        "target_label",
        "ip_address",
        "user_agent",
        "path",
        "method",
        "status_code",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
