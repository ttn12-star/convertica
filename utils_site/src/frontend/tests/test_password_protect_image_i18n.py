"""Native-script SEO copy checks for password-protect-image.

Asserts each target locale's ``.po`` catalog carries the native header
translation. We check the ``.po`` source directly rather than rendering the
page: the CI *test* job does not run ``compilemessages`` (``.mo`` files are
gitignored and only compiled at container start on deploy), so a render-based
assertion fails in CI while passing locally where stale ``.mo`` exist. Live
render across locales was verified manually before release.
"""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

# Header msgid (the tool config's ``header_text``) that carries the native title.
HEADER_MSGID = "Password Protect Image"

# lang prefix -> native-script header the locale's .po must map HEADER_MSGID to
NATIVE_HEADERS = {
    "ru": "Запаролить фото",
    "id": "Kunci Foto dengan Password",
    "ar": "قفل الصور بكلمة مرور",
}


def _msgstr_for(po_path: Path, msgid: str) -> str | None:
    """Return the single-line msgstr for an exact msgid, or None if absent."""
    lines = po_path.read_text(encoding="utf-8").splitlines()
    target = f'msgid "{msgid}"'
    for i, line in enumerate(lines):
        if line.strip() == target:
            for nxt in lines[i + 1 :]:
                if nxt.startswith("msgstr "):
                    return nxt[len('msgstr "') : -1]
                if nxt.strip() == "" or nxt.startswith("msgid"):
                    break
    return None


class PasswordProtectImageI18nTestCase(SimpleTestCase):
    def test_native_header_translation_present_per_locale(self):
        locale_dir = Path(settings.LOCALE_PATHS[0])
        for lang, expected in NATIVE_HEADERS.items():
            with self.subTest(lang=lang):
                po = locale_dir / lang / "LC_MESSAGES" / "django.po"
                self.assertTrue(po.exists(), f"missing .po for {lang}: {po}")
                got = _msgstr_for(po, HEADER_MSGID)
                self.assertEqual(
                    got,
                    expected,
                    f"{lang}: msgstr for {HEADER_MSGID!r} is {got!r}, "
                    f"expected native {expected!r}",
                )
