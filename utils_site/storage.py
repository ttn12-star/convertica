from urllib.parse import unquote, urlsplit, urlunsplit

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class NonStrictManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """ManifestStaticFilesStorage that falls back to the unhashed path when a
    file is missing from the manifest (e.g. in CI where collectstatic has not
    been run).  In production the manifest is always present so all files get
    their hashed URL.

    Django 5.2 changed manifest_strict=False to call hashed_name() (reads the
    file from STATIC_ROOT) instead of returning the plain name.  We override
    stored_name() to restore the simple fallback behaviour.
    """

    manifest_strict = False

    def stored_name(self, name):
        parsed_name = urlsplit(unquote(name))
        clean_name = parsed_name.path.strip()
        cache_name = self.hashed_files.get(self.hash_key(clean_name))
        if cache_name is None:
            # Not in manifest — return unhashed name without touching the disk.
            return self.clean_name(name)
        unparsed_name = list(parsed_name)
        unparsed_name[2] = cache_name
        # Special-case for @font-face hack: url(myfont.eot?#iefix)
        if "?#" in name and not unparsed_name[3]:
            unparsed_name[2] += "?"
        return urlunsplit(unparsed_name)
