from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_seed_questions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="questionitem",
            name="input_type",
            field=models.CharField(
                choices=[
                    ("text", "Short text"),
                    ("textarea", "Long text"),
                    ("integer", "Whole number"),
                    ("decimal", "Decimal number"),
                    ("money", "Amount (KES)"),
                    ("percent", "Percent"),
                    ("year", "Year"),
                    ("date", "Date"),
                    ("email", "Email"),
                    ("tel", "Telephone"),
                    ("choice", "Dropdown list"),
                ],
                default="text",
                max_length=20,
            ),
        ),
    ]
