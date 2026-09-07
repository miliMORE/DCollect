from django.db import migrations


def apply_copy(apps, schema_editor):
    from catalog.question_seed import apply_questionnaire_copy

    apply_questionnaire_copy()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_question_date_type"),
        ("collection", "0009_questionnaire_section_updates"),
    ]

    operations = [
        migrations.RunPython(apply_copy, noop),
    ]
