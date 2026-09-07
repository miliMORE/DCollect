import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_src_executive_grades"),
    ]

    operations = [
        migrations.AddField(
            model_name="benefittype",
            name="is_required",
            field=models.BooleanField(
                default=True,
                help_text="If required, the county must mark whether the benefit is provided.",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="jobs_require_src_equivalent",
            field=models.BooleanField(
                default=False,
                help_text="County must select an SRC equivalent for each applicable benchmark job.",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="require_complete_to_submit",
            field=models.BooleanField(
                default=True,
                help_text="County cannot submit until required questionnaire items, jobs, benefits and documents are complete.",
            ),
        ),
        migrations.CreateModel(
            name="QuestionItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("section", models.CharField(db_index=True, max_length=2)),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("label", models.CharField(max_length=300)),
                ("help_text", models.CharField(blank=True, max_length=400)),
                (
                    "input_type",
                    models.CharField(
                        choices=[
                            ("text", "Short text"),
                            ("textarea", "Long text"),
                            ("integer", "Whole number"),
                            ("decimal", "Decimal number"),
                            ("money", "Amount (KES)"),
                            ("percent", "Percent"),
                            ("year", "Year"),
                            ("email", "Email"),
                            ("tel", "Telephone"),
                            ("choice", "Dropdown list"),
                        ],
                        default="text",
                        max_length=20,
                    ),
                ),
                ("is_required", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("is_builtin", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "option_set",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="questions",
                        to="catalog.optionset",
                    ),
                ),
            ],
            options={"ordering": ["section", "sort_order", "label"]},
        ),
    ]
