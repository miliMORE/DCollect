from django.db import migrations


def retire(apps, schema_editor):
    from catalog.question_seed import seed_questions

    seed_questions()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_questionnaire_copy"),
    ]

    operations = [
        migrations.RunPython(retire, noop),
    ]
