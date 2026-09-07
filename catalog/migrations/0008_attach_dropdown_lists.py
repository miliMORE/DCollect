from django.db import migrations


def seed(apps, schema_editor):
    from catalog.question_seed import seed_questions

    seed_questions()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0007_retire_removed_document_questions"),
    ]

    operations = [
        migrations.RunPython(seed, noop),
    ]
