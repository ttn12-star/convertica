from django.db import migrations
from django.db.models.functions import Upper


def uppercase_conversion_type(apps, schema_editor):
    """Merge case-split analytics labels: word_to_pdf + WORD_TO_PDF -> WORD_TO_PDF.

    The same tool was recorded under two labels depending on whether its view
    declared CONVERSION_TYPE (upper) or fell back to the lowercase URL view_name,
    fragmenting every per-tool report. Uppercasing is deterministic and keeps the
    dev-API endpoints distinct (MERGE_PDF vs MERGE_PDF_API). One UPDATE.
    """
    OperationRun = apps.get_model("users", "OperationRun")
    OperationRun.objects.exclude(conversion_type="").update(
        conversion_type=Upper("conversion_type")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0025_pageviewdaily"),
    ]

    operations = [
        # Irreversible: original casing can't be recovered. noop reverse so the
        # migration can still be unapplied without error.
        migrations.RunPython(uppercase_conversion_type, migrations.RunPython.noop),
    ]
