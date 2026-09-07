from pathlib import Path

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_legacy_files(apps, schema_editor):
    CaseDocument = apps.get_model("collection", "CaseDocument")
    CaseDocumentFile = apps.get_model("collection", "CaseDocumentFile")
    for doc in CaseDocument.objects.exclude(file=""):
        CaseDocumentFile.objects.create(
            document=doc,
            file=doc.file,
            original_name=Path(doc.file.name).name if doc.file else "",
            uploaded_at=doc.uploaded_at,
            uploaded_by_id=doc.uploaded_by_id,
        )
        doc.file = ""
        doc.save(update_fields=["file"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("collection", "0009_questionnaire_section_updates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="casedocument",
            name="document_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="slots",
                to="catalog.documenttype",
            ),
        ),
        migrations.CreateModel(
            name="CaseDocumentFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="cases/%Y/%m/")),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("uploaded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="collection.casedocument",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["uploaded_at", "id"]},
        ),
        migrations.RunPython(copy_legacy_files, noop),
    ]
