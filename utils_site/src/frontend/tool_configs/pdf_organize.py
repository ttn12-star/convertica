"""PDF organisation tool configurations (merge, split, compress, etc.)."""

from django.utils.translation import gettext_lazy as _

PDF_ORGANIZE_CONFIGS = {
    "merge_pdf": {
        "template": "frontend/pdf_organize/merge_pdf.html",
        "converter_args": {
            "page_title": _("Merge PDF Files Online Free - Combine PDFs | Convertica"),
            "page_description": _(
                "Merge PDF online free. Combine multiple PDF files into one document. "
                "Drag and drop to reorder, no watermark, no registration. "
                "Fast & secure PDF merger for all devices."
            ),
            "page_keywords": (
                # Primary keywords
                "merge PDF, combine PDF, merge pdf online free, join pdf files, "
                "combine two pdfs into one, merge pdf without watermark, pdf merger, "
                # Feature-based keywords
                "merge pdf drag and drop, merge pdf reorder pages, merge pdf preserve bookmarks, "
                "merge pdf no quality loss, merge pdf keep links, combine pdf pages in order, "
                # Use case keywords
                "merge pdf thesis chapters, merge pdf invoices, merge pdf contracts, "
                "merge pdf scanned pages, merge pdf receipts, combine pdf statements, "
                "merge pdf lecture notes, merge pdf business documents, merge pdf reports, "
                # Quantity keywords
                "merge 2 pdf files, merge 3 pdfs, merge multiple pdf files, merge 10 pdfs, "
                "combine several pdfs, batch merge pdf, merge many pdfs at once, "
                # Platform keywords
                "merge pdf online, merge pdf mac, merge pdf windows, merge pdf mobile, "
                "merge pdf iphone, merge pdf android, merge pdf chromebook, "
                # Free/No registration keywords
                "merge pdf free, merge pdf no registration, merge pdf no sign up, "
                "pdf merger unlimited, merge pdf safe, merge pdf secure, "
                # Comparison keywords
                "smallpdf merge alternative, ilovepdf merge alternative, pdf merge best 2026"
            ),
            "page_subtitle": _("Combine multiple PDF files into one document"),
            "header_text": _("Merge PDF"),
            "file_input_name": "pdf_files",
            "file_accept": ".pdf",
            "api_url_name": "merge_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Merge PDFs"),
            "select_file_message": _("Please select PDF files to merge."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Drag & Drop Reorder"),
                    "description": _(
                        "Easily arrange PDF files in any order by dragging and dropping"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("No Quality Loss"),
                    "description": _(
                        "Original PDF quality preserved. No compression, no watermarks added"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Secure Processing"),
                    "description": _(
                        "Files are encrypted during processing and deleted immediately after"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Merge Up to 10 Files"),
                    "description": _(
                        "Combine 2-10 PDF files at once. Premium users can merge even more"
                    ),
                },
            ],
            "benefits_title": _("Why Merge PDFs with Convertica?"),
            "page_faq": [
                {
                    "question": _("How many PDF files can I merge at once?"),
                    "answer": _(
                        "Free users can merge 2-10 PDF files in one operation. Simply select all your files, "
                        "arrange them in the desired order using drag and drop, and click Merge. "
                        "Premium users can merge even more files with higher page limits."
                    ),
                },
                {
                    "question": _("Will bookmarks and links be preserved?"),
                    "answer": _(
                        "Yes, internal bookmarks and hyperlinks within each PDF are preserved after merging. "
                        "The merged PDF will contain all bookmarks from all source files, making navigation easy."
                    ),
                },
                {
                    "question": _(
                        "Can I change the order of PDF files before merging?"
                    ),
                    "answer": _(
                        "Yes! After selecting your files, you can drag and drop them to arrange in any order. "
                        "Preview thumbnails help you see which file is which. The final merged PDF will follow "
                        "the order you set."
                    ),
                },
                {
                    "question": _("Is there a file size limit for merging?"),
                    "answer": _(
                        "Free users can merge PDFs with a combined total of up to 50 pages. "
                        "For larger documents, Premium subscription provides higher limits. "
                        "There's no limit on individual file sizes."
                    ),
                },
                {
                    "question": _("Can I merge scanned PDFs?"),
                    "answer": _(
                        "Yes, you can merge both digital and scanned PDFs. The tool combines them "
                        "as-is without any conversion. All pages from all files will be included "
                        "in the merged document."
                    ),
                },
            ],
            "faq_title": _("Merge PDF - Frequently Asked Questions"),
            "page_tips": [
                _(
                    "Arrange files in the correct order before merging - use drag and drop to reorder"
                ),
                _(
                    "For large projects, merge related chapters or sections separately first"
                ),
                _(
                    "Check page orientation - rotate pages if needed before or after merging"
                ),
                _("Remove unnecessary pages before merging to keep file size small"),
                _(
                    "After merging, you can use our Split tool to extract specific pages if needed"
                ),
            ],
            "tips_title": _("Tips for Merging PDF Files"),
            "page_content_title": _("Merge PDF Files Online - Easy & Free"),
            "page_content_body": _(
                "<p>Need to combine multiple PDF documents into a single file? Our <strong>free PDF merger</strong> "
                "lets you join 2-10 PDF files quickly and easily. Perfect for combining "
                "<strong>invoices, contracts, reports, or scanned documents</strong>.</p>"
                "<p>Simply select your files, arrange them in the desired order using drag and drop, "
                "and click Merge. Your combined PDF will be ready for download in seconds. "
                "All <strong>bookmarks, hyperlinks, and formatting</strong> are preserved.</p>"
                "<p><strong>Use cases:</strong> Combine thesis chapters, merge scanned receipts, "
                "join contract pages, create document packages for clients, or organize lecture notes "
                "into a single file.</p>"
            ),
        },
    },
    "split_pdf": {
        "template": "frontend/pdf_organize/split_pdf.html",
        "converter_args": {
            "page_title": _(
                "Split PDF Online Free - Extract Pages from PDF | Convertica"
            ),
            "page_description": _(
                "Split PDF online free. Extract specific pages, split by ranges, "
                "or separate every page. No watermark, no registration. "
                "Fast PDF splitter for all devices."
            ),
            "page_keywords": (
                # Primary keywords
                "split PDF, divide PDF, split pdf online free, pdf splitter, "
                "separate pdf into pages, extract pages from pdf, "
                # Feature keywords
                "split pdf by pages, split pdf by range, split pdf every page, "
                "split pdf into multiple files, pdf splitter no watermark, "
                "extract specific pages pdf, split pdf without quality loss, "
                # Use case keywords
                "extract pdf chapters, split thesis pdf, extract invoice pages, "
                "split pdf for printing, extract odd pages pdf, extract even pages, "
                "remove front page pdf, extract pdf cover page, split scanned pdf, "
                # Platform keywords
                "pdf splitter online, split pdf mac, split pdf windows, split pdf mobile, "
                "pdf splitter iphone, pdf splitter android, "
                # Free keywords
                "split pdf free, pdf splitter no registration, split pdf no ads, "
                "pdf splitter unlimited, split pdf safe, split pdf secure"
            ),
            "page_subtitle": _("Split your PDF into multiple files"),
            "header_text": _("Split PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "split_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".zip",
            "button_text": _("Split PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Multiple Split Options"),
                    "description": _(
                        "Split by page ranges, extract every page, or select specific pages"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("No Quality Loss"),
                    "description": _(
                        "Original PDF quality preserved. Pages extracted exactly as they are"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Download as ZIP"),
                    "description": _(
                        "All split pages downloaded as a single ZIP file for convenience"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Secure & Private"),
                    "description": _(
                        "Files deleted immediately after processing. Your documents stay private"
                    ),
                },
            ],
            "benefits_title": _("Why Split PDFs with Convertica?"),
            "page_faq": [
                {
                    "question": _("How do I split a PDF by page ranges?"),
                    "answer": _(
                        "Enter the page ranges you want to extract, such as '1-5, 8, 10-15'. "
                        "Each range will be saved as a separate PDF file. You can also extract "
                        "every page individually by selecting 'Split every page'."
                    ),
                },
                {
                    "question": _("Can I extract specific pages from a PDF?"),
                    "answer": _(
                        "Yes! Enter the page numbers you want, separated by commas (e.g., '1, 3, 5, 7'). "
                        "Each specified page will be extracted to a new PDF file. "
                        "You can combine individual pages and ranges."
                    ),
                },
                {
                    "question": _("Will splitting affect the quality of my PDF?"),
                    "answer": _(
                        "No, splitting preserves the original quality. Pages are extracted exactly as they are "
                        "in the original document, with no re-compression or quality loss. "
                        "All text, images, and formatting remain intact."
                    ),
                },
                {
                    "question": _("How do I download the split pages?"),
                    "answer": _(
                        "After splitting, all extracted pages are packaged into a ZIP file for easy download. "
                        "The ZIP contains individual PDF files named with the page numbers or ranges you specified."
                    ),
                },
                {
                    "question": _("Is there a limit on how many pages I can split?"),
                    "answer": _(
                        "Free users can split PDFs up to 50 pages. Premium users have higher limits. "
                        "For very large documents, you may need to process them in batches."
                    ),
                },
            ],
            "faq_title": _("Split PDF - Frequently Asked Questions"),
            "page_tips": [
                _("Use ranges like '1-5, 10-15' to extract multiple sections at once"),
                _("Select 'Split every page' to create individual PDFs from each page"),
                _(
                    "Extract odd or even pages only for double-sided printing preparation"
                ),
                _(
                    "For large PDFs, split into smaller parts for easier sharing via email"
                ),
                _("After splitting, use Merge PDF to combine pages in a new order"),
            ],
            "tips_title": _("Tips for Splitting PDF Files"),
            "page_content_title": _("Split PDF Online - Extract Pages Easily"),
            "page_content_body": _(
                "<p>Need to extract specific pages from a PDF? Our <strong>free PDF splitter</strong> "
                "lets you divide PDF documents by page ranges, extract individual pages, "
                "or split every page into separate files.</p>"
                "<p>Perfect for <strong>extracting chapters from ebooks, separating invoices, "
                "splitting contracts, or preparing documents for printing</strong>. "
                "The original quality is preserved - no compression or quality loss.</p>"
                "<p><strong>Flexible options:</strong> Enter page ranges (1-5, 10-15), "
                "individual pages (1, 3, 7), or split every page. All extracted pages "
                "download as a convenient ZIP file.</p>"
            ),
        },
    },
    "remove_pages": {
        "template": "frontend/pdf_organize/remove_pages.html",
        "converter_args": {
            "page_title": _("Remove Pages from PDF Online Free | Convertica"),
            "page_description": _(
                "Remove pages from PDF online free. "
                "Delete unwanted pages quickly and easily with no watermark. "
                "Fast PDF page removal tool. Perfect for cleaning up documents. "
                "No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "remove PDF pages, delete PDF pages, remove pages from pdf online free, "
                "pdf page remover, delete pages from pdf, pdf page deletion tool, "
                # Feature keywords
                "remove pdf pages no watermark, delete pdf pages fast, "
                "remove pdf pages without losing quality, remove multiple pages pdf, "
                "delete specific pages pdf, remove first page pdf, remove last page pdf, "
                # Use case keywords
                "remove blank pages pdf, delete cover page pdf, remove unwanted pages pdf, "
                "clean up pdf, remove advertisements pdf, delete empty pages pdf, "
                "remove intro pages pdf, delete appendix pdf, trim pdf pages, "
                # Quality keywords
                "remove pages pdf keep quality, delete pages pdf no compression, "
                # Platform keywords
                "pdf page removal mac, pdf page removal windows, remove pdf pages online, "
                "delete pdf pages mobile, remove pdf pages iphone, remove pdf pages android, "
                # Free keywords
                "remove pdf pages free, remove pdf pages no registration, remove pdf pages no signup, "
                "delete pdf pages free online, pdf page remover unlimited, "
                # Comparison keywords
                "smallpdf delete pages alternative, ilovepdf remove pages alternative"
            ),
            "page_subtitle": _("Remove unwanted pages from your PDF"),
            "header_text": _("Remove Pages"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "remove_pages_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Remove Pages"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>',
                    "gradient": "from-red-500 to-red-600",
                    "title": _("Quick Page Deletion"),
                    "description": _("Remove unwanted pages from your PDF in seconds"),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Quality Preserved"),
                    "description": _("Original content quality remains unchanged"),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Visual Preview"),
                    "description": _("See page thumbnails before removing"),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Processing"),
                    "description": _("Fast removal with immediate download"),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I remove pages from a PDF?"),
                    "answer": _(
                        "Upload your PDF, select the pages you want to remove, and click Remove Pages."
                    ),
                },
                {
                    "question": _("Can I remove multiple pages at once?"),
                    "answer": _(
                        "Yes! Select multiple pages by clicking on them or using ranges like '1,3,5' or '1-5'."
                    ),
                },
                {
                    "question": _("Will removing pages affect the document quality?"),
                    "answer": _(
                        "No, removing pages only deletes the selected pages. Remaining content stays unchanged."
                    ),
                },
                {
                    "question": _("Can I undo page removal after saving?"),
                    "answer": _(
                        "No, page removal is permanent once you download the new PDF. "
                        "Always keep a backup of your original file before removing pages."
                    ),
                },
                {
                    "question": _("How do I remove blank pages from a PDF?"),
                    "answer": _(
                        "Upload your PDF, view the page thumbnails to identify blank pages, "
                        "select them by clicking or using page numbers, then click Remove Pages. "
                        "This is perfect for cleaning up scanned documents."
                    ),
                },
            ],
            "page_tips": [
                _("Preview pages before removing to avoid mistakes"),
                _("Use page ranges for faster selection (e.g., '1-3, 7, 10-12')"),
                _("Remove blank pages to reduce file size"),
                _("Keep a backup of your original PDF before removing pages"),
                _(
                    "Use Extract Pages instead if you want to keep specific pages as a new document"
                ),
            ],
            "page_content_title": _("Remove Pages from PDF - Delete Unwanted Pages"),
            "page_content_body": _(
                "<p>Our free PDF page remover lets you delete unwanted pages from any PDF document. "
                "Perfect for removing blank pages, cover pages, or unnecessary content.</p>"
                "<p>Simply upload your PDF, preview the pages using thumbnails, select the ones you want "
                "to remove, and download the cleaned-up document. The remaining pages maintain their "
                "original quality and formatting.</p>"
                "<p><strong>Common uses:</strong> Remove blank pages from scanned documents, delete cover pages "
                "or advertisements, trim unnecessary appendices, or clean up exported presentations before sharing.</p>"
            ),
        },
    },
    "extract_pages": {
        "template": "frontend/pdf_organize/extract_pages.html",
        "converter_args": {
            "page_title": _("Extract Pages from PDF Online Free | Convertica"),
            "page_description": _(
                "Extract pages from PDF online free. "
                "Select and extract specific pages to create a new PDF. "
                "Fast PDF page extraction tool with no watermark. "
                "Perfect for creating custom documents. No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "extract PDF pages, PDF page extractor, extract pages from pdf online free, "
                "select pdf pages, pdf page extraction tool, get specific pages from pdf, "
                # Feature keywords
                "extract pdf pages no watermark, extract specific pages pdf, "
                "extract pdf pages by range, extract pdf pages by number, "
                "extract single page from pdf, extract multiple pages pdf, "
                # Use case keywords
                "extract chapter from pdf, extract cover page pdf, extract table of contents pdf, "
                "extract odd pages pdf, extract even pages pdf, extract first page pdf, "
                "extract last page pdf, extract middle pages pdf, extract specific section pdf, "
                # Quality keywords
                "extract pdf pages keep quality, extract pages pdf no compression, "
                # Platform keywords
                "extract pdf pages mac, extract pdf pages windows, extract pdf pages online, "
                "extract pdf pages mobile, extract pdf pages iphone, extract pdf pages android, "
                # Free keywords
                "extract pdf pages free, extract pdf pages no registration, extract pdf pages no signup, "
                "pdf page extractor unlimited, extract pages pdf safe, "
                # Comparison keywords
                "smallpdf extract pages alternative, ilovepdf extract alternative"
            ),
            "page_subtitle": _("Extract specific pages from your PDF"),
            "header_text": _("Extract Pages"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "extract_pages_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Extract Pages"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Flexible Selection"),
                    "description": _(
                        "Extract individual pages, ranges, or specific combinations"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Quality Preserved"),
                    "description": _("Extracted pages maintain original quality"),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("New PDF Created"),
                    "description": _(
                        "Get a new PDF containing only your selected pages"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Processing"),
                    "description": _("Fast extraction with immediate download"),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I extract specific pages from a PDF?"),
                    "answer": _(
                        "Upload your PDF, select the pages you want (e.g., '1,3,5' or '1-10'), and click Extract."
                    ),
                },
                {
                    "question": _("What's the difference between Extract and Split?"),
                    "answer": _(
                        "Extract creates one new PDF with selected pages. Split creates multiple separate PDFs."
                    ),
                },
                {
                    "question": _("Can I extract non-consecutive pages?"),
                    "answer": _(
                        "Yes! Use comma-separated page numbers like '1,3,7,15' to extract specific pages."
                    ),
                },
                {
                    "question": _(
                        "Will extracted pages maintain their original quality?"
                    ),
                    "answer": _(
                        "Yes, extracted pages are identical to the originals. No compression or quality loss occurs. "
                        "All text, images, and formatting remain exactly as in the source PDF."
                    ),
                },
                {
                    "question": _("Can I extract pages from a password-protected PDF?"),
                    "answer": _(
                        "You'll need to unlock the PDF first using our Unlock PDF tool. "
                        "Once unlocked, you can extract any pages you need."
                    ),
                },
            ],
            "page_tips": [
                _("Use ranges for consecutive pages (e.g., '1-10')"),
                _("Combine ranges and individual pages (e.g., '1-5,8,10-15')"),
                _("Preview pages before extracting to ensure correct selection"),
                _("Extract odd or even pages for double-sided printing needs"),
                _("Use Extract instead of Split when you need just one combined PDF"),
            ],
            "page_content_title": _("Extract Pages from PDF - Create Custom Documents"),
            "page_content_body": _(
                "<p>Our free PDF page extractor lets you select and extract specific pages to create "
                "a new PDF document. Perfect for extracting chapters, important sections, or creating "
                "custom document packages.</p>"
                "<p>Select individual pages, ranges like '1-10', or combinations like '1-5, 8, 12-15'. "
                "The extracted pages are combined into a new PDF that you can download immediately. "
                "All formatting and quality are preserved.</p>"
                "<p><strong>Common uses:</strong> Extract specific chapters from ebooks, pull out important "
                "contract sections, create document excerpts for sharing, extract forms from multi-page documents, "
                "or prepare specific pages for printing.</p>"
            ),
        },
    },
    "organize_pdf": {
        "template": "frontend/pdf_organize/organize_pdf.html",
        "converter_args": {
            "page_title": _("Organize PDF Online Free - Reorder Pages | Convertica"),
            "page_description": _(
                "Organize PDF online free. "
                "Reorder pages, sort content, and manage your PDF files "
                "with drag and drop. Fast PDF organizer with no watermark. "
                "Perfect for organizing documents and reports. No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "organize PDF, PDF organizer, organize pdf online free, "
                "reorder pdf pages, pdf page organizer, rearrange pdf pages, "
                # Feature keywords
                "reorder pdf pages drag and drop, sort pdf pages, change pdf page order, "
                "move pdf pages, swap pdf pages, pdf page sorting tool, "
                # Use case keywords
                "organize pdf for presentation, fix pdf page order, reorder scanned pdf, "
                "sort pdf documents, fix scanned document order, organize report pages, "
                "arrange pdf slides, reorder contract pages, organize thesis chapters, "
                # Quality keywords
                "reorder pdf pages no quality loss, organize pdf keep formatting, "
                # Platform keywords
                "organize pdf mac, organize pdf windows, reorder pdf online, "
                "pdf organizer mobile, reorder pdf iphone, reorder pdf android, "
                # Free keywords
                "organize pdf free, organize pdf no registration, reorder pdf no signup, "
                "pdf organizer unlimited, organize pdf no watermark, "
                # Comparison keywords
                "smallpdf organize alternative, ilovepdf reorder alternative"
            ),
            "page_subtitle": _("Organize and manage your PDF documents"),
            "header_text": _("Organize PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "organize_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Organize PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Drag & Drop Reorder"),
                    "description": _("Easily rearrange pages by dragging and dropping"),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Page Thumbnails"),
                    "description": _(
                        "See visual previews of all pages for easy organization"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Quality Preserved"),
                    "description": _(
                        "Page order changes without affecting content quality"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Processing"),
                    "description": _("Save your new page order with one click"),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I reorder pages in a PDF?"),
                    "answer": _(
                        "Upload your PDF, drag and drop page thumbnails to rearrange them, then click Save."
                    ),
                },
                {
                    "question": _("Can I also delete pages while organizing?"),
                    "answer": _(
                        "Use our dedicated Remove Pages tool to delete pages. Organize is for reordering only."
                    ),
                },
                {
                    "question": _("Will reordering affect the document quality?"),
                    "answer": _(
                        "No, reordering only changes page sequence. All content remains unchanged."
                    ),
                },
                {
                    "question": _("Can I move multiple pages at once?"),
                    "answer": _(
                        "Yes, you can select multiple pages and drag them together to a new position. "
                        "This makes it easy to move entire sections of your document."
                    ),
                },
                {
                    "question": _(
                        "Is there a limit on the number of pages I can organize?"
                    ),
                    "answer": _(
                        "Free users can organize PDFs with up to 50 pages. "
                        "For larger documents, Premium subscription provides higher limits."
                    ),
                },
            ],
            "page_tips": [
                _("Use page thumbnails to identify pages quickly"),
                _("Drag multiple pages at once for bulk reordering"),
                _("Review the final order before saving"),
                _("Combine with Merge PDF to organize pages from multiple documents"),
                _("Use Rotate PDF first if some pages are upside down"),
            ],
            "page_content_title": _("Organize PDF Pages - Reorder and Rearrange"),
            "page_content_body": _(
                "<p>Our free PDF organizer lets you reorder pages in any PDF document using simple "
                "drag and drop. Perfect for fixing page order, organizing scanned documents, "
                "or preparing presentations.</p>"
                "<p>Simply upload your PDF, view page thumbnails, and drag pages to rearrange them. "
                "The visual interface makes it easy to see exactly how your document will look. "
                "All content and formatting remain unchanged.</p>"
                "<p><strong>Common uses:</strong> Fix incorrectly ordered scanned documents, "
                "rearrange presentation slides, organize report sections, reorder contract pages, "
                "or prepare documents for printing in the correct sequence.</p>"
            ),
        },
    },
    "compress_pdf": {
        "template": "frontend/pdf_organize/compress_pdf.html",
        "converter_args": {
            "page_title": _("Compress PDF Online Free - Reduce PDF Size | Convertica"),
            "page_description": _(
                "Compress PDF online free to reduce file size. "
                "Shrink PDF for email (under 1MB), no quality loss. "
                "No watermark, no registration. Fast PDF compressor for all devices."
            ),
            "page_keywords": (
                # Primary keywords
                "compress PDF, PDF compressor, compress pdf online free, reduce pdf file size, "
                "shrink pdf, pdf optimizer, make pdf smaller, pdf size reducer, "
                # Size-specific keywords
                "compress pdf to 1mb, compress pdf to 500kb, compress pdf under 10mb, "
                "compress pdf under 25mb gmail, compress pdf for email attachment, "
                "reduce pdf to under 1mb, heavy pdf to small pdf, "
                # Quality keywords
                "compress pdf no quality loss, compress pdf keep quality, compress pdf without blur, "
                "compress pdf high quality, pdf compression best quality, shrink pdf readable, "
                # Use case keywords
                "compress pdf for email, compress pdf for web, compress pdf for printing, "
                "compress scanned pdf, compress pdf images, compress invoice pdf, "
                "compress academic pdf, compress ebook pdf, compress pdf presentation, "
                # Platform keywords
                "compress pdf online, compress pdf mac, compress pdf windows, compress pdf mobile, "
                "compress pdf iphone, compress pdf android, compress pdf from phone, "
                # Free/No registration keywords
                "compress pdf free, compress pdf no registration, compress pdf no watermark, "
                "pdf compressor unlimited, compress pdf safe, compress pdf secure, "
                # Percentage keywords
                "compress pdf 50 percent, compress pdf 90 percent, reduce pdf size by half, "
                # Comparison keywords
                "smallpdf compress alternative, ilovepdf compress alternative, best pdf compressor 2026"
            ),
            "page_subtitle": _("Reduce PDF file size without losing quality"),
            "header_text": _("Compress PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "compress_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Compress PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Reduce Up to 90%"),
                    "description": _(
                        "Significantly reduce PDF file size while maintaining readable quality"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Perfect for Email"),
                    "description": _(
                        "Compress PDFs to under 1MB for email attachments that won't bounce"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Keep Text Sharp"),
                    "description": _(
                        "Smart compression preserves text clarity while reducing image size"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Fast Processing"),
                    "description": _(
                        "Compress even large PDFs in seconds with our optimized algorithms"
                    ),
                },
            ],
            "benefits_title": _("Why Compress PDFs with Convertica?"),
            "page_faq": [
                {
                    "question": _("How much can I reduce my PDF file size?"),
                    "answer": _(
                        "Results vary depending on the content, but you can typically reduce PDF size by 50-90%. "
                        "PDFs with many images compress more than text-only documents. "
                        "Scanned documents usually achieve the best compression ratios."
                    ),
                },
                {
                    "question": _("Will compression affect text quality?"),
                    "answer": _(
                        "No, text remains sharp and readable. Our smart compression algorithm primarily "
                        "optimizes images and removes unnecessary metadata while preserving text clarity. "
                        "The document remains fully searchable and selectable."
                    ),
                },
                {
                    "question": _("Can I compress a PDF to exactly 1MB for email?"),
                    "answer": _(
                        "Our compressor optimizes the file as much as possible while maintaining quality. "
                        "For most documents, you'll get a file under 1MB. If the result is still too large, "
                        "try splitting the PDF first, then compressing each part."
                    ),
                },
                {
                    "question": _("Is the compressed PDF still printable?"),
                    "answer": _(
                        "Yes, compressed PDFs are fully printable. While images are optimized for screen viewing, "
                        "text and vector graphics remain at full quality. For high-quality printing needs, "
                        "we recommend keeping the original file."
                    ),
                },
                {
                    "question": _("Can I compress scanned documents?"),
                    "answer": _(
                        "Yes! Scanned PDFs often benefit the most from compression since they contain large images. "
                        "Our tool can significantly reduce the size of scanned documents while keeping "
                        "the content readable."
                    ),
                },
            ],
            "faq_title": _("Compress PDF - Frequently Asked Questions"),
            "page_tips": [
                _("PDFs with images compress better than text-only documents"),
                _("For email attachments, aim for under 10MB (or 25MB for Gmail)"),
                _(
                    "If the file is still too large after compression, try splitting it first"
                ),
                _("Scanned documents usually achieve 70-90%% size reduction"),
                _("Keep the original file if you need maximum print quality"),
            ],
            "tips_title": _("Tips for PDF Compression"),
            "page_content_title": _("Compress PDF Online - Reduce File Size Instantly"),
            "page_content_body": _(
                "<p>Need to send a large PDF by email? Our <strong>free PDF compressor</strong> "
                "reduces file size significantly while maintaining readable quality. Perfect for "
                "<strong>email attachments, web uploads, and storage optimization</strong>.</p>"
                "<p>The tool uses smart compression algorithms that optimize images and remove unnecessary "
                "metadata while keeping text sharp and documents fully searchable. Most PDFs can be "
                "reduced by <strong>50-90%</strong> in size.</p>"
                "<p><strong>Common uses:</strong> Compress PDFs for email (under 25MB for Gmail), "
                "reduce scanned document sizes, optimize PDFs for website upload, "
                "shrink presentation exports, and prepare files for mobile viewing.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT1M",
        },
    },
}
