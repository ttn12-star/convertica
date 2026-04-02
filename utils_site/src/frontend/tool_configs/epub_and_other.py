"""EPUB and other format tool configurations."""

from django.utils.translation import gettext_lazy as _

EPUB_AND_OTHER_CONFIGS = {
    "epub_to_pdf": {
        "template": "frontend/premium/epub_to_pdf.html",
        "converter_args": {
            "page_title": _("EPUB to PDF Converter (Premium) - Convertica"),
            "page_description": _(
                "Convert EPUB eBooks to PDF online with premium quality rendering. "
                "Preserve chapter structure, text flow, and typography for printing and sharing. "
                "Higher limits for long books."
            ),
            "page_keywords": (
                "epub to pdf premium, epub converter, ebook to pdf, "
                "convert epub online, epub book to pdf"
            ),
            "page_subtitle": _("Convert EPUB books to printable PDF documents"),
            "header_text": _("EPUB to PDF Converter"),
            "file_input_name": "epub_file",
            "file_accept": ".epub",
            "api_url_name": "epub_to_pdf_api",
            "replace_regex": r"\.epub$",
            "replace_to": ".pdf",
            "button_text": _("Convert EPUB to PDF"),
            "select_file_message": _("Please select an EPUB file."),
            "button_class": "bg-amber-600 text-white hover:bg-amber-700",
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Chapter-aware conversion"),
                    "description": _(
                        "EPUB spine order and heading hierarchy are mapped into readable PDF flow."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-blue-500 to-indigo-600",
                    "title": _("Premium rendering quality"),
                    "description": _(
                        "Designed for long-form eBooks with stable pagination and clean typography."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7h18M3 12h18M3 17h18"/>',
                    "gradient": "from-emerald-500 to-teal-600",
                    "title": _("Higher limits"),
                    "description": _(
                        "Handle larger files and longer books than standard free converters."
                    ),
                },
            ],
            "benefits_title": _("Why use EPUB to PDF in Premium?"),
            "page_faq": [
                {
                    "question": _("Is EPUB to PDF available for free users?"),
                    "answer": _(
                        "EPUB to PDF conversion is a premium feature. You can open this page and review the workflow, but conversion requires an active premium subscription."
                    ),
                },
                {
                    "question": _("Will chapter structure be preserved in PDF output?"),
                    "answer": _(
                        "Yes, chapter order and text flow are preserved when source EPUB markup is valid. Complex custom styles may be simplified for better compatibility."
                    ),
                },
                {
                    "question": _("What file size and page limits apply?"),
                    "answer": _(
                        "Premium limits allow larger source files and significantly more pages than free tools. Exact limits are shown on the pricing page and enforced during upload."
                    ),
                },
            ],
            "faq_title": _("EPUB to PDF FAQ"),
            "page_tips": [
                _(
                    "Use EPUB files with semantic headings for cleaner PDF chapter structure."
                ),
                _(
                    "Embedded fonts improve consistency between original eBook and PDF output."
                ),
                _(
                    "If layout looks dense, check source CSS and remove unnecessary overrides."
                ),
                _(
                    "For very large eBooks, split archives by volume for faster processing."
                ),
            ],
            "tips_title": _("Tips for Better EPUB to PDF Output"),
            "page_content_title": _(
                "Convert EPUB to PDF with chapter-aware formatting"
            ),
            "page_content_body": _(
                "<p><strong>EPUB to PDF</strong> is ideal when you need printable, shareable, "
                "and archive-friendly versions of eBooks. The converter keeps chapter order and "
                "core text structure so the output remains comfortable to read offline.</p>"
                "<p>Premium processing is tuned for larger eBook inputs and longer documents, "
                "making it suitable for manuals, educational content, and internal documentation.</p>"
                "<p>For best quality, upload EPUB files with clean markup, consistent heading "
                "levels, and embedded fonts.</p>"
            ),
        },
        "extra": {
            "offer_price": "6",
            "offer_currency": "USD",
        },
    },
    "pdf_to_epub": {
        "template": "frontend/premium/pdf_to_epub.html",
        "converter_args": {
            "page_title": _("PDF to EPUB Converter (Premium) - Convertica"),
            "page_description": _(
                "Convert PDF documents to EPUB format for eReaders with premium tools. "
                "Extract text and build chapter-based EPUB output."
            ),
            "page_keywords": (
                "pdf to epub premium, pdf converter to ebook, "
                "convert pdf to epub online, pdf to ebook"
            ),
            "page_subtitle": _("Convert PDF files to eReader-friendly EPUB format"),
            "header_text": _("PDF to EPUB Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_epub_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".epub",
            "button_text": _("Convert PDF to EPUB"),
            "select_file_message": _("Please select a PDF file."),
            "button_class": "bg-amber-600 text-white hover:bg-amber-700",
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7h12M4 12h8m-8 5h12m4-10v10a2 2 0 01-2 2h-1"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Reader-friendly reflow"),
                    "description": _(
                        "Transforms fixed PDF pages into EPUB text flow optimized for eReaders."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h18v14H3V5zm3 3h12M6 11h10M6 14h7"/>',
                    "gradient": "from-blue-500 to-indigo-600",
                    "title": _("Preserved structure"),
                    "description": _(
                        "Detects headings and paragraphs to keep document hierarchy in EPUB."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6l4 2m5-2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-emerald-500 to-teal-600",
                    "title": _("Prepared for long reads"),
                    "description": _(
                        "Good fit for books, reports, and archives you want to read on mobile devices."
                    ),
                },
            ],
            "benefits_title": _("Why use PDF to EPUB in Premium?"),
            "page_faq": [
                {
                    "question": _("Can scanned PDFs be converted to EPUB?"),
                    "answer": _(
                        "Scanned PDFs should be OCR-processed first. Text-based PDFs produce much cleaner EPUB output with better chapter and paragraph detection."
                    ),
                },
                {
                    "question": _("Does the converter keep headings and sections?"),
                    "answer": _(
                        "Yes. The converter maps detected heading hierarchy and paragraphs into EPUB-friendly structure where possible."
                    ),
                },
                {
                    "question": _("Will images from PDF appear in EPUB?"),
                    "answer": _(
                        "Most embedded images are carried over. Very complex page layouts can be simplified to maintain reading compatibility in common eReader apps."
                    ),
                },
            ],
            "faq_title": _("PDF to EPUB FAQ"),
            "page_tips": [
                _("Text-based PDFs convert more accurately than image-only scans."),
                _("Remove decorative pages and heavy watermarks before conversion."),
                _(
                    "Keep heading hierarchy clear in source PDFs to improve EPUB navigation."
                ),
                _("If needed, run OCR first and then convert OCR output to EPUB."),
            ],
            "tips_title": _("Tips for Better PDF to EPUB Output"),
            "page_content_title": _("Convert PDF to EPUB for eReader-ready publishing"),
            "page_content_body": _(
                "<p><strong>PDF to EPUB</strong> helps convert static page layouts into flexible, "
                "reader-friendly eBook format. The output is easier to consume on phones, tablets, "
                "and dedicated eReaders.</p>"
                "<p>Premium conversion focuses on preserving headings and paragraph logic so "
                "navigation remains predictable across reading apps.</p>"
                "<p>For the cleanest EPUB result, use text-based PDFs or run OCR first on scanned files.</p>"
            ),
        },
        "extra": {
            "offer_price": "6",
            "offer_currency": "USD",
        },
    },
    "pdf_to_markdown": {
        "template": "frontend/premium/pdf_to_markdown.html",
        "converter_args": {
            "page_title": _("PDF to Markdown Converter (Premium) - Convertica"),
            "page_description": _(
                "Convert PDF documents to Markdown with preserved heading structure and "
                "table formatting. Ideal for docs, notes, and knowledge bases."
            ),
            "page_keywords": (
                "pdf to markdown premium, convert pdf to markdown, pdf markdown converter, "
                "pdf to md with tables, pdf headings to markdown"
            ),
            "page_subtitle": _(
                "Extract clean Markdown with heading hierarchy and table blocks"
            ),
            "header_text": _("PDF to Markdown Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_markdown_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".md",
            "button_text": _("Convert PDF to Markdown"),
            "select_file_message": _("Please select a PDF file."),
            "button_class": "bg-amber-600 text-white hover:bg-amber-700",
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h10M4 18h7"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Heading hierarchy extraction"),
                    "description": _(
                        "Maps visual heading levels into Markdown syntax for clean document structure."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7h18M3 12h18M3 17h18M7 3v18M12 3v18M17 3v18"/>',
                    "gradient": "from-blue-500 to-indigo-600",
                    "title": _("Table-aware export"),
                    "description": _(
                        "Converts detectable tables into Markdown-friendly rows and columns."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-emerald-500 to-teal-600",
                    "title": _("Docs and knowledge base ready"),
                    "description": _(
                        "Useful for wikis, README files, product docs, and migration pipelines."
                    ),
                },
            ],
            "benefits_title": _("Why use PDF to Markdown in Premium?"),
            "page_faq": [
                {
                    "question": _("Does PDF to Markdown preserve headings?"),
                    "answer": _(
                        "Yes. The converter detects heading levels from typography and document structure, then maps them to Markdown heading syntax."
                    ),
                },
                {
                    "question": _("Are tables exported as Markdown tables?"),
                    "answer": _(
                        "When table structure is detectable, tables are exported in Markdown-compatible format. Complex nested tables may be simplified."
                    ),
                },
                {
                    "question": _("Who can use PDF to Markdown?"),
                    "answer": _(
                        "PDF to Markdown is a premium feature. Free users can browse the page, while conversion endpoints require active premium access."
                    ),
                },
            ],
            "faq_title": _("PDF to Markdown FAQ"),
            "page_tips": [
                _(
                    "Enable heading detection to preserve section structure in exported Markdown."
                ),
                _("Keep table extraction enabled for reports with tabular data."),
                _(
                    "Run OCR first for scanned PDFs to improve text quality in Markdown."
                ),
                _(
                    "Review output in your editor and adjust edge cases like merged cells."
                ),
            ],
            "tips_title": _("Tips for Better PDF to Markdown Output"),
            "page_content_title": _(
                "Convert PDF to Markdown with heading and table structure"
            ),
            "page_content_body": _(
                "<p><strong>PDF to Markdown</strong> is useful when you need editable plain-text "
                "documentation from PDF sources. It helps transform reports, guides, and manuals "
                "into version-control friendly files.</p>"
                "<p>Premium mode improves structure recovery by detecting headings and converting "
                "supported tables into Markdown format for downstream editing.</p>"
                "<p>This workflow is especially practical for documentation teams moving content "
                "from PDFs into internal wikis and repositories.</p>"
            ),
        },
        "extra": {
            "offer_price": "6",
            "offer_currency": "USD",
        },
    },
}
