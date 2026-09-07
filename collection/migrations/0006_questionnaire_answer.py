import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_questions_and_form_rules"),
        ("collection", "0005_clarification_created_by_optional"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionnaireAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.TextField(blank=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="catalog.questionitem",
                    ),
                ),
                (
                    "questionnaire",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extra_answers",
                        to="collection.questionnaire",
                    ),
                ),
            ],
            options={
                "unique_together": {("questionnaire", "question")},
            },
        ),
    ]
