"""Content checks for the /pdf-editor/ strings across all target locales.

Asserts each locale's ``.po`` catalog carries a translated msgstr for the new
PDF-editor msgids. We check the ``.po`` source directly rather than rendering
the page: the CI *test* job does not run ``compilemessages`` (``.mo`` files are
gitignored and only compiled at container start on deploy), so a render-based
assertion fails in CI while passing locally where stale ``.mo`` exist. Live
render across locales was verified manually before release.
"""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_LOCALES = ("ru", "es", "pl", "id", "hi", "ar")

# Anchor msgids introduced by the /pdf-editor/ tool (page H1 + a FAQ question).
_ANCHOR_MSGIDS = (
    "Free Online PDF Editor",
    "Is this PDF editor really free?",
    "PDF Editor FAQ",
)


def _msgstr_for(po_path: Path, msgid: str) -> str | None:
    """Return the (possibly multi-line) msgstr for an exact single-line msgid.

    Returns None if the msgid is absent. The msgstr is the concatenation of
    its continuation string literals (leading ``msgstr "..."`` + following
    ``"..."`` lines), unescaped only enough to tell empty from non-empty.
    """
    lines = po_path.read_text(encoding="utf-8").splitlines()
    target = f'msgid "{msgid}"'
    for i, line in enumerate(lines):
        if line.strip() != target:
            continue
        j = i + 1
        # Skip any continuation lines of a multi-line msgid (none for anchors).
        while j < len(lines) and lines[j].startswith('"'):
            j += 1
        if j >= len(lines) or not lines[j].startswith("msgstr "):
            return None
        parts = [lines[j][len('msgstr "') : -1]]
        j += 1
        while j < len(lines) and lines[j].startswith('"'):
            parts.append(lines[j][1:-1])
            j += 1
        return "".join(parts)
    return None


class PdfEditorI18nTestCase(SimpleTestCase):
    def test_anchor_msgids_translated_in_every_locale(self):
        locale_dir = Path(settings.LOCALE_PATHS[0])
        for lang in _LOCALES:
            po = locale_dir / lang / "LC_MESSAGES" / "django.po"
            self.assertTrue(po.exists(), f"missing .po for {lang}: {po}")
            for msgid in _ANCHOR_MSGIDS:
                with self.subTest(lang=lang, msgid=msgid):
                    got = _msgstr_for(po, msgid)
                    self.assertIsNotNone(
                        got, f"{lang}: msgid {msgid!r} missing from catalog"
                    )
                    self.assertTrue(
                        got.strip(),
                        f"{lang}: msgid {msgid!r} has empty msgstr",
                    )
