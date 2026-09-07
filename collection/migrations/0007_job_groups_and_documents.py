import django.db.models.deletion
from django.db import migrations, models


def wipe_job_rows(apps, schema_editor):
    JobPayRow = apps.get_model("collection", "JobPayRow")
    JobPayRow.objects.all().delete()


def update_catalogues(apps, schema_editor):
    QuestionItem = apps.get_model("catalog", "QuestionItem")
    DocumentType = apps.get_model("catalog", "DocumentType")
    QuestionItem.objects.update(is_required=False)
    DocumentType.objects.update(is_required=False)
    DocumentType.objects.filter(code__in=["payroll-extract", "hr-policy"]).update(is_active=False)
    DocumentType.objects.filter(code="positions-list").update(
        name="List of positions/designations (The staff establishment)"
    )
    DocumentType.objects.update_or_create(
        code="cba",
        defaults={
            "name": "Relevant CBA (where applicable)",
            "is_required": False,
            "is_active": True,
            "sort_order": 90,
        },
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_seed_questions"),
        ("collection", "0006_questionnaire_answer"),
    ]

    operations = [
        migrations.RunPython(wipe_job_rows, noop),
        migrations.AlterUniqueTogether(
            name="jobpayrow",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="jobpayrow",
            name="job",
        ),
        migrations.RemoveField(
            model_name="jobpayrow",
            name="src_equivalent",
        ),
        migrations.AddField(
            model_name="jobpayrow",
            name="job_group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="county_pay_rows",
                to="catalog.jobgroup",
            ),
        ),
        migrations.AddField(
            model_name="jobpayrow",
            name="src_equivalent",
            field=models.CharField(
                blank=True,
                help_text="SRC denotation for this job group as used by the county, for example EX4.",
                max_length=40,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="jobpayrow",
            unique_together={("case", "job_group")},
        ),
        migrations.AlterModelOptions(
            name="jobpayrow",
            options={"ordering": ["job_group__sort_order", "job_group__code"]},
        ),
        migrations.AddField(
            model_name="casedocument",
            name="not_available",
            field=models.BooleanField(
                default=False,
                help_text="Allowed only when the document type is optional.",
            ),
        ),
        migrations.RunPython(update_catalogues, noop),
    ]
