"""Runnable check for the Excel->PDF print-fit preprocessing.

Pure openpyxl assertions (no LibreOffice) so it is safe in CI. Verifies the
branch that fixes wide tables spilling across PDF pages ("table shifted").

Run standalone:  python test_print_fit.py
Or via pytest:   pytest test_print_fit.py
"""

import os
import tempfile

import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from src.api.pdf_convert.excel_to_pdf.utils import _apply_print_fit


def _make_xlsx(path, cols, col_width=None, preconfigured=False):
    wb = openpyxl.Workbook()
    ws = wb.active
    for j in range(1, cols + 1):
        ws.cell(1, j, f"C{j}")
        if col_width:
            ws.column_dimensions[get_column_letter(j)].width = col_width
    if preconfigured:  # author already set a manual print scale
        ws.page_setup.scale = 60
    wb.save(path)


def test_wide_table_fits_and_goes_landscape():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "wide.xlsx")
        _make_xlsx(p, cols=25, col_width=14)
        _apply_print_fit(p, {})
        ws = openpyxl.load_workbook(p).active
        assert ws.page_setup.fitToWidth == 1
        assert ws.page_setup.fitToHeight == 0
        assert ws.sheet_properties.pageSetUpPr.fitToPage is True
        assert ws.page_setup.orientation == "landscape"


def test_narrow_table_fits_but_stays_portrait():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "narrow.xlsx")
        _make_xlsx(p, cols=4)  # default width -> well under threshold
        _apply_print_fit(p, {})
        ws = openpyxl.load_workbook(p).active
        assert ws.page_setup.fitToWidth == 1
        # not forced into landscape
        assert ws.page_setup.orientation != "landscape"


def test_author_print_scale_is_respected():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "authored.xlsx")
        _make_xlsx(p, cols=25, col_width=14, preconfigured=True)
        _apply_print_fit(p, {})
        ws = openpyxl.load_workbook(p).active
        # We must not clobber a deliberate manual scale.
        assert ws.page_setup.scale == 60
        assert ws.page_setup.fitToWidth != 1


def test_non_xlsx_is_noop():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "legacy.xls")
        with open(p, "wb") as f:
            f.write(b"\xd0\xcf\x11\xe0not-a-real-xls")
        before = os.path.getsize(p)
        _apply_print_fit(p, {})  # must not raise
        assert os.path.getsize(p) == before


def test_forced_portrait_overrides_wide_heuristic():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "wide.xlsx")
        _make_xlsx(p, cols=25, col_width=14)  # would auto-go landscape
        _apply_print_fit(p, {}, orientation="portrait")
        ws = openpyxl.load_workbook(p).active
        assert ws.page_setup.orientation == "portrait"
        assert ws.page_setup.fitToWidth == 1  # still fits width


def test_actual_mode_leaves_size_untouched():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "wide.xlsx")
        _make_xlsx(p, cols=25, col_width=14)
        _apply_print_fit(p, {}, fit_mode="actual")
        ws = openpyxl.load_workbook(p).active
        # No fit-to-width forced -> table keeps native size (may span pages).
        assert ws.page_setup.fitToWidth != 1


def test_user_choice_overrides_author_scale():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "authored.xlsx")
        _make_xlsx(p, cols=25, col_width=14, preconfigured=True)
        # Explicit user pick must win over the author's manual scale.
        _apply_print_fit(p, {}, orientation="landscape")
        ws = openpyxl.load_workbook(p).active
        assert ws.page_setup.orientation == "landscape"


def test_paper_defaults_to_a4_but_author_letter_stays():
    # No paperSize means US Letter in OOXML; every converted sheet came out Letter.
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "paper.xlsx")
        wb = openpyxl.Workbook()
        wb.active["A1"] = "x"
        letter = wb.create_sheet("Letter")
        letter["A1"] = "x"
        letter.page_setup.paperSize = 1
        wb.save(p)
        _apply_print_fit(p, {}, fit_mode="actual")
        wb = openpyxl.load_workbook(p)
        assert int(wb.worksheets[0].page_setup.paperSize) == 9
        assert int(wb.worksheets[1].page_setup.paperSize) == 1


def test_whitespace_past_the_table_is_emptied_and_nothing_else():
    # A lone " " in AZ500 shrank the whole table to 2.4pt and added a blank page.
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "stray.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        for r in range(1, 31):
            for c in range(1, 7):
                ws.cell(r, c, f"r{r}c{c}")
        ws["C5"] = " "  # inside the table: keep
        ws["G2"] = " "  # stops F2's text from running on: keep
        ws["AZ500"] = " "
        ws["AZ500"].fill = PatternFill("solid", fgColor="FFFF00")
        ws.print_title_rows = "1:1"
        fill_only = wb.create_sheet("Fill")
        fill_only["A1"] = "x"
        fill_only["AZ500"].fill = PatternFill("solid", fgColor="FFFF00")
        wb.save(p)
        _apply_print_fit(p, {})
        wb = openpyxl.load_workbook(p)
        ws, fill_only = wb.worksheets
        assert ws["AZ500"].value is None
        assert ws["AZ500"].fill.fgColor.rgb.endswith("FFFF00")  # format kept
        assert ws["C5"].value == " " and ws["G2"].value == " "
        assert ws["F30"].value == "r30c6"
        assert ws.print_title_rows == "$1:$1", ws.print_title_rows
        # A fill alone isn't printed: no flip to landscape.
        assert fill_only.page_setup.orientation != "landscape"


def test_books_with_formulas_keep_their_blanks():
    # COUNTA/ISBLANK over a " " would change once LibreOffice recalculates.
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "formulas.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["a", "b"])
        ws["B8"] = " "
        ws["E1"] = "=COUNTA(B1:B100)"
        wb.save(p)
        _apply_print_fit(p, {})
        assert openpyxl.load_workbook(p).active["B8"].value == " "


if __name__ == "__main__":
    test_wide_table_fits_and_goes_landscape()
    test_narrow_table_fits_but_stays_portrait()
    test_author_print_scale_is_respected()
    test_non_xlsx_is_noop()
    test_forced_portrait_overrides_wide_heuristic()
    test_actual_mode_leaves_size_untouched()
    test_user_choice_overrides_author_scale()
    test_paper_defaults_to_a4_but_author_letter_stays()
    test_whitespace_past_the_table_is_emptied_and_nothing_else()
    test_books_with_formulas_keep_their_blanks()
    print("OK: all print-fit checks passed")
