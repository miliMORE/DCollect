from django.db import migrations


def seed(apps, schema_editor):
    from catalog.question_seed import seed_questions

    seed_questions()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_questions_and_form_rules"),
    ]

    operations = [
        migrations.RunPython(seed, noop),
    ]
