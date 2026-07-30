"""Give the SITE_ID row a name and domain.

On prod both fields are empty strings, which leaked into every allauth email
("Hello from !", "register an account on .", subject "[] Please Confirm ...").
The email templates no longer read Site, but anything else that calls
get_current_site() would hit the same hole, so fill it once.

Only empty fields are filled, and ``domain`` is unique — a deploy must never
fail on an IntegrityError here, so it is skipped if another row already owns it.
"""

from django.conf import settings
from django.db import migrations

DOMAIN = "convertica.net"


def fill_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    site_id = getattr(settings, "SITE_ID", 1)
    domain_free = not Site.objects.filter(domain=DOMAIN).exclude(pk=site_id).exists()

    site = Site.objects.filter(pk=site_id).first()
    if site is None:
        if domain_free:
            Site.objects.create(pk=site_id, name="Convertica", domain=DOMAIN)
        return

    site.name = site.name or "Convertica"
    if not site.domain and domain_free:
        site.domain = DOMAIN
    site.save(update_fields=["name", "domain"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0029_align_plan_prices_with_seed"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(fill_site, migrations.RunPython.noop),
    ]
