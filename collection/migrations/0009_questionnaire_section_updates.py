from django.db import migrations, models
from django.core.validators import MaxValueValidator, MinValueValidator


def copy_answers(apps, schema_editor):
    Questionnaire = apps.get_model("collection", "Questionnaire")
    equity_map = {
        "Partially equitable": "Moderately equitable",
        "Not equitable": "Inequitable",
    }
    for row in Questionnaire.objects.all():
        changed = False
        if row.main_allowances and not row.remunerative_allowances:
            row.remunerative_allowances = row.main_allowances
            changed = True
        mapped = equity_map.get(row.internal_equity)
        if mapped:
            row.internal_equity = mapped
            changed = True
        if changed:
            row.save(update_fields=["remunerative_allowances", "internal_equity"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0008_alter_jobpayrow_median_basic"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionnaire",
            name="remunerative_allowances",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="non_remunerative_allowances",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="gratuity_pct",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=6,
                null=True,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="retention_challenge_reasons",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="questionnaire",
            name="recruitment_challenges",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="questionnaire",
            name="medical_insurance",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(copy_answers, noop),
    ]
