from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("collection", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionnaire",
            name="salary_structure_attached",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="payroll_extract_attached",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="allowance_schedule_attached",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="benefits_schedule_attached",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="hr_policy_attached",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
