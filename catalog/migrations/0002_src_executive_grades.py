from django.db import migrations


EX_GRADES = (
    (0, "EX1", "SRC equivalent EX1"),
    (0, "EX2", "SRC equivalent EX2"),
    (0, "EX3", "SRC equivalent EX3"),
    (0, "EX4", "SRC equivalent EX4"),
    (0, "EX5", "SRC equivalent EX5"),
)


def add_ex_grades(apps, schema_editor):
    SRCGrade = apps.get_model("catalog", "SRCGrade")
    for sort_order, code, name in EX_GRADES:
        SRCGrade.objects.get_or_create(
            code=code,
            defaults={"name": name, "sort_order": sort_order, "is_active": True},
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_ex_grades, noop),
    ]
