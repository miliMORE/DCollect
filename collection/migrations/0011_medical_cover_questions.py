from django.db import migrations, models


def seed_and_order(apps, schema_editor):
    from catalog.question_seed import seed_questions
    from collection.questionnaire_spec import SECTION_FIELDS

    seed_questions()
    QuestionItem = apps.get_model("catalog", "QuestionItem")
    for index, code in enumerate(SECTION_FIELDS["e"], 1):
        QuestionItem.objects.filter(code=code, is_builtin=True).update(
            section="e", sort_order=index * 10, is_active=True
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0010_document_attachments"),
        ("catalog", "0008_attach_dropdown_lists"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionnaire",
            name="medical_cover_how",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="medical_cover_notes",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(seed_and_order, noop),
    ]
