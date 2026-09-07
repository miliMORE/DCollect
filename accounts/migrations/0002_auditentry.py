import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("catalog", "0001_initial"),
        ("collection", "0004_jobpayrow_src_equivalent"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor_username", models.CharField(blank=True, max_length=150)),
                ("actor_name", models.CharField(blank=True, max_length=200)),
                ("actor_role", models.CharField(blank=True, max_length=40)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("auth", "Sign-in and security"),
                            ("users", "User administration"),
                            ("collection", "County files"),
                            ("settings", "Catalogue and settings"),
                            ("comparators", "Comparators"),
                            ("reports", "Reports and analysis"),
                            ("staff", "Staff survey"),
                            ("audit", "Audit trail"),
                            ("admin", "Django administration"),
                            ("other", "Other"),
                        ],
                        db_index=True,
                        default="other",
                        max_length=20,
                    ),
                ),
                ("action", models.CharField(db_index=True, max_length=80)),
                ("summary", models.CharField(max_length=255)),
                ("detail", models.TextField(blank=True)),
                (
                    "outcome",
                    models.CharField(
                        choices=[("success", "Succeeded"), ("failure", "Failed")],
                        default="success",
                        max_length=12,
                    ),
                ),
                ("target_label", models.CharField(blank=True, max_length=255)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("path", models.CharField(blank=True, max_length=255)),
                ("method", models.CharField(blank=True, max_length=10)),
                ("status_code", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "case",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_entries",
                        to="collection.countycase",
                    ),
                ),
                (
                    "county",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_entries",
                        to="catalog.county",
                    ),
                ),
            ],
            options={
                "verbose_name": "Audit entry",
                "verbose_name_plural": "Audit trail",
                "ordering": ["-created_at"],
            },
        ),
    ]
