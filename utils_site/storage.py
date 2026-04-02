from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class NonStrictManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """ManifestStaticFilesStorage with manifest_strict=False.

    Silently falls back to the unhashed path when a file is missing from the
    manifest (e.g. in CI where collectstatic has not been run).  In production
    the manifest is always present so all files get their hashed URL.
    """

    manifest_strict = False
