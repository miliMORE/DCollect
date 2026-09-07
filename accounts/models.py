from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        COLLECTION_ADMIN = "collection_admin", "Collection administrator"
        CONSULTANT = "consultant", "Field consultant"
        COUNTY = "county", "County respondent"
        ANALYST = "analyst", "Analyst"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COUNTY)
    county = models.ForeignKey(
        "catalog.County",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
        help_text="Required for county respondents. Leave blank for other roles.",
    )
    phone = models.CharField(max_length=40, blank=True)
    must_change_password = models.BooleanField(default=True)
    job_title = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_collection_admin_role(self):
        return self.role == self.Role.COLLECTION_ADMIN

    @property
    def is_consultant_role(self):
        return self.role == self.Role.CONSULTANT or self.is_admin_role

    @property
    def is_analyst_role(self):
        return (
            self.role
            in {
                self.Role.ANALYST,
                self.Role.CONSULTANT,
                self.Role.ADMIN,
                self.Role.COLLECTION_ADMIN,
            }
            or self.is_superuser
        )

    @property
    def is_county_role(self):
        return self.role == self.Role.COUNTY

    @property
    def can_review(self):
        return (
            self.role in {self.Role.ADMIN, self.Role.COLLECTION_ADMIN, self.Role.CONSULTANT}
            or self.is_superuser
        )

    def can_analyse(self):
        return self.is_analyst_role

    @property
    def can_configure(self):
        return self.is_admin_role or self.is_collection_admin_role

    @property
    def can_edit_site(self):
        return self.is_admin_role

    @property
    def can_see_audit(self):
        return self.is_admin_role

    @property
    def can_see_help(self):
        return not self.is_collection_admin_role


class AuditEntry(models.Model):
    class Category(models.TextChoices):
        AUTH = "auth", "Sign-in and security"
        USERS = "users", "User administration"
        COLLECTION = "collection", "County files"
        SETTINGS = "settings", "Catalogue and settings"
        COMPARATORS = "comparators", "Comparators"
        REPORTS = "reports", "Reports and analysis"
        STAFF = "staff", "Staff survey"
        AUDIT = "audit", "Audit trail"
        ADMIN = "admin", "Django administration"
        OTHER = "other", "Other"

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Succeeded"
        FAILURE = "failure", "Failed"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        "User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    actor_name = models.CharField(max_length=200, blank=True)
    actor_role = models.CharField(max_length=40, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER, db_index=True)
    action = models.CharField(max_length=80, db_index=True)
    summary = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    outcome = models.CharField(max_length=12, choices=Outcome.choices, default=Outcome.SUCCESS)
    county = models.ForeignKey(
        "catalog.County",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    case = models.ForeignKey(
        "collection.CountyCase",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    target_label = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit entry"
        verbose_name_plural = "Audit trail"

    def __str__(self):
        who = self.actor_name or self.actor_username or "Unknown"
        return f"{self.created_at:%Y-%m-%d %H:%M} · {who} · {self.summary}"

    def actor_role_label(self):
        return dict(User.Role.choices).get(self.actor_role, self.actor_role or "—")
