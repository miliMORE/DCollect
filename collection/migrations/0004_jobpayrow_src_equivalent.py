import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_src_executive_grades"),
        ("collection", "0003_staff_survey"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobpayrow",
            name="src_equivalent",
            field=models.ForeignKey(
                blank=True,
                help_text="SRC denotation for this post as used by the county. May differ from the county job group (for example Job Group S → EX4).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="county_job_rows",
                to="catalog.srcgrade",
            ),
        ),
        migrations.AlterField(
            model_name="jobpayrow",
            name="median_basic",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Kept for analysis if previously entered. Respondents no longer input this; analysis uses the midpoint of min and max when blank.",
                max_digits=14,
                null=True,
            ),
        ),
    ]
