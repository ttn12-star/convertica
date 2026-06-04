"""Repoint django_admin_log.user_id FK to the custom user table.

On production the `django_admin_log.user_id` foreign key still references the
legacy `auth_user` table (it was created before this project switched to the
custom `users.User` model). Every admin save writes a LogEntry whose user_id is
the editing admin's id, which lives in `users_user` — so the commit fails with:

    IntegrityError: insert or update on table "django_admin_log" violates
    foreign key constraint "django_admin_log_user_id_..._fk_auth_user_id"
    DETAIL: Key (user_id)=(N) is not present in table "auth_user".

The failing LogEntry insert rolls back the whole admin transaction, so e.g.
granting premium via the admin returns HTTP 500 and silently does nothing.

This migration drops whatever FK currently sits on django_admin_log.user_id and
re-adds it pointing at users_user. The new constraint is added NOT VALID so it
does not choke on any legacy rows whose user_id predates the model switch —
only new/updated rows are enforced, which is all the admin needs.

PostgreSQL-only: SQLite (local/dev) does not enforce this FK and cannot ALTER
constraints this way, so it is a no-op there.
"""

from django.db import migrations

# NB: no literal '%' anywhere — this SQL is passed through psycopg's mogrify,
# which would treat '%' as a parameter placeholder and fail at compose time.
# The FK is located by its column (conkey -> pg_attribute) instead of a LIKE.
FIX_SQL = r"""
DO $$
DECLARE
    cname text;
BEGIN
    -- Find the existing FK on django_admin_log.user_id, whatever it references.
    SELECT con.conname INTO cname
      FROM pg_constraint con
      JOIN pg_attribute att
        ON att.attrelid = con.conrelid
       AND att.attnum = ANY (con.conkey)
     WHERE con.conrelid = 'django_admin_log'::regclass
       AND con.contype = 'f'
       AND att.attname = 'user_id';

    IF cname IS NOT NULL THEN
        EXECUTE 'ALTER TABLE django_admin_log DROP CONSTRAINT ' || quote_ident(cname);
    END IF;

    -- Re-add it pointing at the custom user table. NOT VALID skips validation
    -- of pre-existing rows; new inserts/updates are still checked.
    ALTER TABLE django_admin_log
        ADD CONSTRAINT django_admin_log_user_id_users_user_id_fk
        FOREIGN KEY (user_id) REFERENCES users_user (id)
        DEFERRABLE INITIALLY DEFERRED
        NOT VALID;
END $$;
"""


def fix_admin_log_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(FIX_SQL)


def noop_reverse(apps, schema_editor):
    # Leaving the FK pointing at users_user is correct; nothing to undo.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0021_user_webhook_secret"),
        ("admin", "0003_logentry_add_action_flag_choices"),
    ]

    operations = [
        migrations.RunPython(fix_admin_log_fk, noop_reverse),
    ]
