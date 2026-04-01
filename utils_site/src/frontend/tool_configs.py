"""
Tool configuration data for Convertica PDF tools.

Maps tool keys to converter arguments, SEO data, and template path.
Used by _render_tool_page() in views.py.
"""

from django.utils.translation import gettext_lazy as _

# Batch API routing: api_url_name -> batch endpoint + field name
BATCH_API_MAP = {
    "excel_to_pdf_api": {
        "batch_url": "excel_to_pdf_batch_api",
        "field_name": "excel_files",
    },
    "ppt_to_pdf_api": {"batch_url": "ppt_to_pdf_batch_api", "field_name": "ppt_files"},
    "pdf_to_word_api": {
        "batch_url": "pdf_to_word_batch_api",
        "field_name": "pdf_files",
    },
    "word_to_pdf_api": {
        "batch_url": "word_to_pdf_batch_api",
        "field_name": "word_files",
    },
    "pdf_to_jpg_api": {"batch_url": "pdf_to_jpg_batch_api", "field_name": "pdf_files"},
    "jpg_to_pdf_api": {
        "batch_url": "jpg_to_pdf_batch_api",
        "field_name": "image_files",
    },
    "pdf_to_excel_api": {
        "batch_url": "pdf_to_excel_batch_api",
        "field_name": "pdf_files",
    },
    "pdf_to_ppt_api": {"batch_url": "pdf_to_ppt_batch_api", "field_name": "pdf_files"},
    "pdf_to_html_api": {
        "batch_url": "pdf_to_html_batch_api",
        "field_name": "pdf_files",
    },
    "crop_pdf_api": {"batch_url": "crop_pdf_batch_api", "field_name": "pdf_files"},
    "add_watermark_api": {
        "batch_url": "add_watermark_batch_api",
        "field_name": "pdf_files",
    },
    "add_page_numbers_api": {
        "batch_url": "add_page_numbers_batch_api",
        "field_name": "pdf_files",
    },
    "compress_pdf_api": {
        "batch_url": "compress_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "split_pdf_api": {"batch_url": "split_pdf_batch_api", "field_name": "pdf_files"},
    "extract_pages_api": {
        "batch_url": "extract_pages_batch_api",
        "field_name": "pdf_files",
    },
    "remove_pages_api": {
        "batch_url": "remove_pages_batch_api",
        "field_name": "pdf_files",
    },
    "organize_pdf_api": {
        "batch_url": "organize_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "protect_pdf_api": {
        "batch_url": "protect_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "unlock_pdf_api": {"batch_url": "unlock_pdf_batch_api", "field_name": "pdf_files"},
    "flatten_pdf_api": {
        "batch_url": "flatten_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "pdf_to_text_api": {
        "batch_url": "pdf_to_text_batch_api",
        "field_name": "pdf_files",
    },
    "sign_pdf_api": {
        "batch_url": "sign_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "optimize_image_api": {
        "batch_url": "optimize_image_batch_api",
        "field_name": "image_files",
    },
    "convert_image_api": {
        "batch_url": "convert_image_batch_api",
        "field_name": "image_files",
    },
}


TOOL_CONFIGS = {
    "pdf_to_word": {
        "template": "frontend/pdf_convert/pdf_to_word.html",
        "converter_args": {
            "page_title": _(
                "PDF to Word Converter Online Free - No Registration | Convertica"
            ),
            "page_description": _(
                "Convert PDF to Word online free without losing formatting. "
                "Preserve tables, images & fonts. No registration, no watermark. "
                "Works on Windows, Mac, Linux, iOS, Android. Try now!"
            ),
            "page_keywords": (
                # Primary keywords
                "PDF to Word, convert PDF to Word online free, PDF to DOCX, PDF to Word converter, "
                "convert PDF to Word without losing formatting, PDF to Word no email required, "
                # Feature-based keywords
                "pdf to word keep tables, pdf to word preserve formatting, pdf to word keep images, "
                "pdf to word maintain layout, pdf to word editable, pdf to word searchable, "
                # Use case keywords
                "pdf to word for resume, pdf to word for cv, pdf to word for contract, "
                "pdf to word for invoice, pdf to word for legal documents, pdf to word for thesis, "
                "pdf to word academic paper, pdf to word job application, pdf to word university, "
                # Platform keywords
                "pdf to word mac, pdf to word windows, pdf to word linux, pdf to word chromebook, "
                "pdf to word iphone, pdf to word android, pdf to word mobile, pdf to word tablet, "
                # Quality keywords
                "pdf to word high quality, pdf to word best 2026, pdf to word accurate, "
                "pdf to word clean layout, pdf to word high accuracy, pdf to word no errors, "
                # Free/No registration keywords
                "pdf to word free, pdf to word no registration, pdf to word no sign up, "
                "pdf to word no watermark, pdf to word unlimited, pdf to word safe, "
                # OCR keywords
                "convert scanned pdf to word, pdf to word ocr, scanned image pdf to docx, "
                "pdf to word extract text, best ocr pdf to word free, "
                # Comparison keywords
                "smallpdf alternative, ilovepdf alternative, adobe acrobat alternative"
            ),
            "page_subtitle": _(
                "Convert your PDF documents to editable Word format in seconds"
            ),
            "header_text": _("PDF to Word Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_word_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".docx",
            "button_text": _("Convert PDF to Word"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Preserve Formatting"),
                    "description": _(
                        "Tables, images, fonts, and layout stay intact after conversion"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Completely Free & Secure"),
                    "description": _(
                        "No registration, no watermarks. Files deleted immediately after conversion"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Works on All Devices"),
                    "description": _(
                        "Convert PDF to Word on Windows, Mac, Linux, iOS, Android"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("OCR for Scanned PDFs"),
                    "description": _(
                        "Premium: Convert image-based PDFs to editable text with 15+ languages"
                    ),
                },
            ],
            "benefits_title": _("Why Convert PDF to Word with Convertica?"),
            "page_faq": [
                {
                    "question": _("Can I convert a scanned PDF to Word?"),
                    "answer": _(
                        "Yes! Premium users can enable OCR (Optical Character Recognition) to convert "
                        "scanned PDFs and image-based documents to editable Word format. "
                        "OCR supports 15+ languages including English, Russian, German, French, "
                        "Spanish, Chinese, Japanese, and Arabic for accurate text recognition."
                    ),
                },
                {
                    "question": _("Will my tables and formatting be preserved?"),
                    "answer": _(
                        "Yes, our PDF to Word converter preserves tables, images, fonts, headers, "
                        "footers, and complex layouts. The converted Word document will look "
                        "as close to the original PDF as possible, maintaining text alignment "
                        "and paragraph spacing."
                    ),
                },
                {
                    "question": _("Is this PDF to Word converter really free?"),
                    "answer": _(
                        "Yes, Convertica PDF to Word converter is completely free for standard use. "
                        "No registration required, no email needed, no watermarks added. "
                        "Premium subscription is optional and provides higher page limits and OCR features."
                    ),
                },
                {
                    "question": _("What is the maximum file size I can convert?"),
                    "answer": _(
                        "Free users can convert PDF files up to 50 pages. "
                        "For larger documents, you can split them first using our Split PDF tool, "
                        "or upgrade to Premium for higher limits up to 500 pages per file."
                    ),
                },
                {
                    "question": _("Can I convert PDF to Word on my phone?"),
                    "answer": _(
                        "Yes! Convertica works on all mobile devices - iPhone, iPad, Android phones "
                        "and tablets. Simply open the website in your mobile browser, upload your PDF, "
                        "and download the converted Word document. No app installation required."
                    ),
                },
            ],
            "faq_title": _("PDF to Word Converter - FAQ"),
            "page_tips": [
                _(
                    "Text-based PDFs convert better than scanned documents - for scanned PDFs, enable OCR"
                ),
                _(
                    "For best results, use PDFs created from Word or other text editors, not screenshots"
                ),
                _(
                    "Large files (over 50 pages) may take longer - consider splitting them first"
                ),
                _(
                    "If tables look misaligned, try re-saving the original PDF before converting"
                ),
                _("After conversion, review formatting in Word and adjust if needed"),
            ],
            "tips_title": _("Tips for Best PDF to Word Conversion"),
            "page_content_title": _("Convert PDF to Word Online - Fast & Accurate"),
            "page_content_body": _(
                "<p>Need to edit a PDF document? Our <strong>free PDF to Word converter</strong> "
                "transforms your PDF files into fully editable Word documents (.docx) while "
                "preserving the original formatting, including tables, images, fonts, and layout.</p>"
                "<p>Whether you're converting a <strong>resume, contract, invoice, or academic paper</strong>, "
                "Convertica ensures high-quality PDF to DOCX conversion. Unlike other tools, we maintain "
                "complex formatting elements like multi-column layouts, headers, footers, and embedded graphics.</p>"
                "<p><strong>For scanned PDFs:</strong> Premium users can enable OCR (Optical Character "
                "Recognition) to extract text from image-based PDFs. Our OCR supports 15+ languages "
                "including English, Russian, German, French, Spanish, Chinese, Japanese, and Arabic.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT3M",
        },
    },
    "word_to_pdf": {
        "template": "frontend/pdf_convert/word_to_pdf.html",
        "converter_args": {
            "page_title": _(
                "Word to PDF Converter Free Online - Convert DOCX to PDF | Convertica"
            ),
            "page_description": _(
                "Convert Word to PDF online free without losing formatting. "
                "Preserve fonts, images & layout. No registration, no watermark. "
                "Works on all devices. Fast & secure conversion."
            ),
            "page_keywords": (
                # Primary keywords
                "Word to PDF, DOCX to PDF, DOC to PDF, convert Word to PDF online free, "
                "word to pdf without losing formatting, docx to pdf converter, "
                # Feature-based keywords
                "word to pdf keep fonts, word to pdf preserve layout, word to pdf keep images, "
                "word to pdf maintain formatting, word to pdf high quality, word to pdf export, "
                # Use case keywords
                "convert resume to pdf, word to pdf for cv, word to pdf for contract, "
                "word to pdf for invoice, word to pdf for legal documents, word to pdf for thesis, "
                "word to pdf academic paper, word to pdf job application, word to pdf business, "
                # Platform keywords
                "word to pdf mac, word to pdf windows, word to pdf linux, word to pdf online, "
                "word to pdf iphone, word to pdf android, word to pdf mobile, word to pdf chromebook, "
                # Free/No registration keywords
                "word to pdf free, word to pdf no registration, word to pdf no sign up, "
                "word to pdf no watermark, word to pdf unlimited, word to pdf safe, word to pdf secure, "
                # Batch/Multiple files keywords
                "word to pdf batch converter, convert multiple word to pdf, word to pdf bulk, "
                # Quality keywords
                "word to pdf best 2026, word to pdf fast online, word to pdf one click, "
                "word to pdf clean, word to pdf professional"
            ),
            "page_subtitle": _("Convert your Word documents to PDF format in seconds"),
            "header_text": _("Word to PDF Converter"),
            "file_input_name": "word_file",
            "file_accept": ".doc,.docx",
            "api_url_name": "word_to_pdf_api",
            "replace_regex": r"\.(docx?|DOCX?)$",
            "replace_to": ".pdf",
            "button_text": _("Convert to PDF"),
            "select_file_message": _("Please select a Word file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Perfect Formatting"),
                    "description": _(
                        "Fonts, images, tables, and layout are preserved exactly as in your Word document"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Secure & Private"),
                    "description": _(
                        "Files are encrypted and automatically deleted. Your documents stay private"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Fast Conversion"),
                    "description": _(
                        "Convert Word to PDF in seconds. No waiting, instant download"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Universal Format"),
                    "description": _(
                        "PDF works everywhere - share documents that look the same on any device"
                    ),
                },
            ],
            "benefits_title": _("Why Convert Word to PDF with Convertica?"),
            "page_faq": [
                {
                    "question": _("Will my fonts be preserved in the PDF?"),
                    "answer": _(
                        "Yes! Our Word to PDF converter embeds fonts in the PDF, ensuring your document "
                        "looks exactly the same on any device. This includes custom fonts, special characters, "
                        "and text formatting like bold, italic, and underline."
                    ),
                },
                {
                    "question": _("Can I convert multiple Word files at once?"),
                    "answer": _(
                        "Premium users can use batch conversion to convert multiple Word documents to PDF "
                        "in one go. Simply select all your files and convert them simultaneously. "
                        "Free users can convert files one at a time."
                    ),
                },
                {
                    "question": _("Is the conversion free and without watermark?"),
                    "answer": _(
                        "Yes, Convertica Word to PDF converter is completely free. We never add watermarks "
                        "to your converted PDFs. No registration required, no email needed. "
                        "Premium subscription is optional for higher limits and batch conversion."
                    ),
                },
                {
                    "question": _("Does the converter support DOC and DOCX formats?"),
                    "answer": _(
                        "Yes, we support both older DOC format (Word 97-2003) and modern DOCX format "
                        "(Word 2007 and later). Simply upload your file and we'll convert it to PDF "
                        "regardless of the Word version used to create it."
                    ),
                },
                {
                    "question": _("Can I convert Word to PDF on my phone?"),
                    "answer": _(
                        "Yes! Convertica works on all mobile devices including iPhone, iPad, and Android. "
                        "Open our website in your mobile browser, upload your Word document, "
                        "and download the PDF. No app installation needed."
                    ),
                },
            ],
            "faq_title": _("Word to PDF Converter - FAQ"),
            "page_tips": [
                _(
                    "For best results, use documents created in Microsoft Word or Google Docs"
                ),
                _("Check that all fonts are properly installed before converting"),
                _("Large documents with many images may take longer to convert"),
                _(
                    "If hyperlinks don't work in PDF, ensure they were active in the Word document"
                ),
                _("Use 'Print Layout' view in Word to preview how the PDF will look"),
            ],
            "tips_title": _("Tips for Best Word to PDF Conversion"),
            "page_content_title": _("Convert Word to PDF Online - Fast & Reliable"),
            "page_content_body": _(
                "<p>Need to share a Word document that looks perfect on any device? Our <strong>free Word to PDF "
                "converter</strong> transforms your DOCX and DOC files into professional PDF documents while "
                "preserving all formatting, fonts, images, and layout.</p>"
                "<p>PDF is the universal standard for document sharing - your <strong>resume, contract, report, "
                "or thesis</strong> will look exactly the same whether opened on Windows, Mac, Linux, or mobile devices. "
                "Recipients don't need Microsoft Word to view your documents.</p>"
                "<p><strong>Perfect for professionals:</strong> Convert Word documents to PDF for email attachments, "
                "online submissions, printing, and archiving. All hyperlinks, bookmarks, and table of contents "
                "are preserved in the converted PDF.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT3M",
        },
    },
    "pdf_to_jpg": {
        "template": "frontend/pdf_convert/pdf_to_jpg.html",
        "converter_args": {
            "page_title": _(
                "PDF to JPG Online Free - Convert PDF to Images | Convertica"
            ),
            "page_description": _(
                "Convert PDF to JPG online free with high quality. "
                "PDF to image converter with no watermark, high resolution (300-600 DPI), "
                "batch conversion. Extract images from PDF or convert PDF pages to JPG/PNG. "
                "Perfect for printing, web upload, and social media."
            ),
            "page_keywords": (
                # Primary keywords
                "PDF to JPG, PDF to image, convert PDF to JPG, pdf to jpg online free, "
                "pdf to image converter, PDF to JPG converter, "
                # Quality keywords
                "pdf to png converter high quality, pdf to image no watermark, "
                "pdf to jpg high resolution, pdf to jpg without losing quality, "
                "pdf to jpg best quality online, pdf to jpg hd converter, "
                # DPI/resolution keywords
                "pdf to image converter 300 dpi, 600 dpi pdf to jpg converter, "
                "pdf to jpg high dpi, pdf to image high resolution, "
                # Batch/multiple keywords
                "batch pdf to jpg converter, pdf to jpg convert all pages, "
                "convert multiple pdf pages to jpg, pdf to jpg bulk converter, "
                # Use case keywords
                "pdf to jpg for printing, pdf to jpg for website upload, "
                "pdf to image for instagram, pdf to image for social media, "
                "pdf to jpg for presentation, pdf poster to jpg, "
                # Format keywords
                "pdf to png converter, pdf to jpeg converter, "
                "export pdf pages as images, extract images from pdf, "
                # Platform keywords
                "pdf to jpg converter for mac online, pdf to jpg online mac, "
                "pdf to jpg converter windows, pdf to jpg mobile, "
                # Free/no registration keywords
                "pdf to jpg converter no ads, pdf to jpg unlimited free, "
                "convert pdf to jpg free no registration, pdf to jpg no signup"
            ),
            "page_subtitle": _(
                "Convert PDF pages to high-quality JPG images in seconds"
            ),
            "header_text": _("PDF to JPG Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_jpg_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".zip",
            "button_text": _("Convert PDF to JPG"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("High Quality Images"),
                    "description": _(
                        "Convert PDF to JPG with up to 600 DPI resolution for crisp, clear images"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Batch Conversion"),
                    "description": _(
                        "Convert all PDF pages to images at once and download as ZIP archive"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("No Watermark"),
                    "description": _(
                        "Get clean images without any watermarks or branding on your converted files"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Fast Processing"),
                    "description": _(
                        "Lightning-fast conversion with instant download - no waiting time"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert a PDF to JPG?"),
                    "answer": _(
                        "Simply upload your PDF file, click the Convert button, and download your JPG images. "
                        "All pages will be converted to separate high-quality JPG files and packaged in a ZIP archive."
                    ),
                },
                {
                    "question": _("What resolution are the converted JPG images?"),
                    "answer": _(
                        "Our converter produces high-resolution images at 300 DPI by default, which is perfect for "
                        "printing and professional use. The quality is preserved during conversion."
                    ),
                },
                {
                    "question": _("Can I convert a multi-page PDF to JPG?"),
                    "answer": _(
                        "Yes! When you convert a multi-page PDF, each page becomes a separate JPG image. "
                        "All images are packaged in a convenient ZIP file for easy download."
                    ),
                },
                {
                    "question": _("Is there a limit on PDF file size?"),
                    "answer": _(
                        "Free users can convert PDFs with up to a certain number of pages. "
                        "For larger files, you can split them into smaller parts or upgrade to Premium for higher limits."
                    ),
                },
                {
                    "question": _("Are my PDF files secure?"),
                    "answer": _(
                        "Yes, your files are processed securely and automatically deleted after conversion. "
                        "We don't store or share your documents. Your privacy is our priority."
                    ),
                },
            ],
            "page_tips": [
                _("Use high-quality source PDFs for best image results"),
                _("For printing, ensure your PDF has at least 300 DPI resolution"),
                _("Convert vector-based PDFs for crisp text and graphics"),
                _(
                    "For web use, JPG format offers good compression with acceptable quality"
                ),
                _("Download images as ZIP to keep all pages organized"),
            ],
            "page_content_title": _(
                "PDF to JPG Converter - Extract Images from PDF Online"
            ),
            "page_content_body": _(
                "<p>Our free PDF to JPG converter transforms your PDF documents into high-quality JPG images "
                "with just a few clicks. Whether you need images for presentations, social media, websites, "
                "or printing, our tool delivers crystal-clear results.</p>"
                "<p>The converter preserves the original quality of your PDF content, producing sharp images "
                "suitable for any purpose. Each page of your PDF becomes a separate JPG file, making it easy "
                "to use individual pages wherever you need them.</p>"
                "<p>Perfect for extracting images from PDF documents, creating thumbnails, preparing content "
                "for social media, or converting PDF presentations into image slides.</p>"
            ),
        },
    },
    "jpg_to_pdf": {
        "template": "frontend/pdf_convert/jpg_to_pdf.html",
        "converter_args": {
            "page_title": _(
                "JPG to PDF Online Free - Convert Images to PDF | Convertica"
            ),
            "page_description": _(
                "Convert JPG to PDF online free. Merge multiple images into one PDF "
                "without compression. No watermark, no registration. Works on all devices."
            ),
            "page_keywords": (
                # Primary keywords
                "JPG to PDF, image to PDF, convert JPG to PDF, jpg to pdf online free, "
                "image to pdf converter, photo to PDF, "
                # Quality keywords
                "jpg to pdf without compression, jpg to pdf high quality, "
                "jpg to pdf no watermark, jpg to pdf sharp quality, "
                # Multiple images keywords
                "jpg to pdf merge multiple images, combine images into one pdf, "
                "combine photos to pdf online, multiple images to one pdf, "
                # Use case keywords
                "jpg to pdf for homework, jpg to pdf for university submission, "
                "convert scanned photos to pdf, image to pdf converter for receipts, "
                "convert screenshots to pdf, convert documents to pdf, "
                # Format keywords
                "png to pdf converter, jpeg to pdf, image to pdf, "
                "jpg to pdf for a4 format, photos to pdf, "
                # Platform keywords
                "jpg to pdf converter mac, jpg to pdf online mac, "
                "jpg to pdf converter windows, jpg to pdf mobile, "
                # Free/no registration keywords
                "jpg to pdf converter no ads, jpg to pdf unlimited free, "
                "jpg to pdf free no registration, jpg to pdf no signup"
            ),
            "page_subtitle": _("Convert your JPG images to PDF format in seconds"),
            "header_text": _("JPG to PDF Converter"),
            "file_input_name": "image_file",
            "file_accept": ".jpg,.jpeg",
            "api_url_name": "jpg_to_pdf_api",
            "replace_regex": r"\.(jpg|jpeg|JPG|JPEG)$",
            "replace_to": ".pdf",
            "button_text": _("Convert to PDF"),
            "select_file_message": _("Please select a JPG/JPEG image file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("No Quality Loss"),
                    "description": _(
                        "Convert JPG to PDF without compression - your images stay crystal clear"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Multiple Image Support"),
                    "description": _(
                        "Upload multiple JPG images and combine them into a single PDF document"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Universal Format"),
                    "description": _(
                        "PDF works everywhere - share documents easily with anyone"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Conversion"),
                    "description": _(
                        "Fast processing - convert your images to PDF in seconds"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert a JPG image to PDF?"),
                    "answer": _(
                        "Simply upload your JPG image file, click the Convert button, and download your PDF. "
                        "The conversion happens instantly with no quality loss."
                    ),
                },
                {
                    "question": _("Can I convert multiple JPG images to one PDF?"),
                    "answer": _(
                        "Yes! You can upload multiple JPG images and combine them into a single PDF document. "
                        "Each image will become a separate page in the resulting PDF."
                    ),
                },
                {
                    "question": _("Is the image quality preserved during conversion?"),
                    "answer": _(
                        "Yes, our converter preserves the original quality of your JPG images. "
                        "There is no compression applied during conversion, ensuring your images look exactly the same in the PDF."
                    ),
                },
                {
                    "question": _("What image formats are supported?"),
                    "answer": _(
                        "This converter supports JPG and JPEG image formats. For PNG images, "
                        "please use our PNG to PDF converter or convert your PNG to JPG first."
                    ),
                },
                {
                    "question": _("Is there a file size limit?"),
                    "answer": _(
                        "Free users can convert images up to a certain size. For larger files, "
                        "you may need to resize your images or upgrade to Premium for higher limits."
                    ),
                },
            ],
            "page_tips": [
                _("Use high-resolution images for best PDF quality"),
                _("Ensure proper orientation before uploading for correct page layout"),
                _("For documents, scan at 300 DPI or higher for clear text"),
                _("Crop images before conversion to remove unwanted borders"),
                _("Name your images in order (1.jpg, 2.jpg) for easy organization"),
            ],
            "page_content_title": _(
                "JPG to PDF Converter - Create PDF from Images Online"
            ),
            "page_content_body": _(
                "<p>Our free JPG to PDF converter transforms your images into professional PDF documents "
                "with just one click. Perfect for creating digital portfolios, converting scanned documents, "
                "preparing homework submissions, or archiving photos.</p>"
                "<p>The converter maintains the original image quality - no compression means your photos "
                "and documents look exactly as intended. Each JPG image becomes a full page in the PDF, "
                "making it easy to create multi-page documents from your image collection.</p>"
                "<p>Ideal for students submitting assignments, professionals preparing reports, "
                "photographers creating portfolios, and anyone who needs to share images in PDF format.</p>"
            ),
        },
        "extra": {
            "auto_generate_tool_schema": False,
            "how_to_time": "PT1M",
        },
    },
    "rotate_pdf": {
        "template": "frontend/pdf_edit/rotate_pdf.html",
        "converter_args": {
            "page_title": _("Rotate PDF - Convertica"),
            "page_description": _(
                "Rotate PDF pages online free by 90, 180, or 270 degrees. "
                "Fast PDF rotation tool with no watermark, batch rotation, "
                "and quality preservation. Perfect for scanned documents and "
                "misoriented pages. No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "rotate PDF, PDF rotation, rotate pdf online free, "
                "rotate pdf pages, pdf rotation tool, "
                # Angle keywords
                "rotate pdf pages 90 degrees, rotate pdf pages 180 degrees, "
                "rotate pdf pages 270 degrees, rotate pdf clockwise, "
                "rotate pdf counterclockwise, rotate pdf upside down, "
                # Use case keywords
                "rotate scanned pdf, fix pdf orientation, "
                "rotate pdf for printing, correct pdf page orientation, "
                "rotate pdf document, rotate pdf for mobile, "
                # Quality keywords
                "rotate pdf without losing quality, rotate pdf no watermark, "
                "pdf rotation maintain quality, rotate pdf high quality, "
                # Platform keywords
                "pdf rotation for mac online, rotate pdf windows, "
                "rotate pdf mobile, rotate pdf android, rotate pdf iphone, "
                # Free keywords
                "rotate pdf free no registration, rotate pdf no ads, "
                "rotate pdf unlimited, rotate pdf one click"
            ),
            "page_subtitle": _("Rotate your PDF pages in seconds"),
            "header_text": _("Rotate PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "rotate_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Rotate PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Multiple Rotation Angles"),
                    "description": _(
                        "Rotate pages by 90°, 180°, or 270° - clockwise or counterclockwise"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Quality Preserved"),
                    "description": _(
                        "All content, formatting, and images stay intact after rotation"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Selective Rotation"),
                    "description": _(
                        "Rotate all pages, current page, or specify exact pages to rotate"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Processing"),
                    "description": _(
                        "Fast rotation with immediate download - no waiting required"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I rotate a PDF page?"),
                    "answer": _(
                        "Upload your PDF file, select the rotation angle (90°, 180°, or 270°), "
                        "choose which pages to rotate, and click the Rotate button. Your rotated PDF "
                        "will be ready to download instantly."
                    ),
                },
                {
                    "question": _("Can I rotate specific pages in a PDF?"),
                    "answer": _(
                        "Yes! You can rotate all pages, just the current page, or specify exact page numbers. "
                        "Use formats like '1,3,5' for individual pages or '1-5' for a range."
                    ),
                },
                {
                    "question": _("Will rotating affect the PDF quality?"),
                    "answer": _(
                        "No, our rotation tool preserves all content, formatting, images, and text quality. "
                        "The rotation only changes the page orientation without any quality loss."
                    ),
                },
                {
                    "question": _("How do I fix a sideways scanned PDF?"),
                    "answer": _(
                        "Upload your scanned PDF, select 90° (clockwise) or 270° (counterclockwise) "
                        "depending on how the document is oriented, and rotate it to fix the orientation."
                    ),
                },
                {
                    "question": _("Is there a limit on PDF file size?"),
                    "answer": _(
                        "Free users can rotate PDFs with up to a certain number of pages. "
                        "For larger files, split them or upgrade to Premium for higher limits."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "Preview your PDF before rotating to identify which pages need rotation"
                ),
                _("Use 90° clockwise to rotate a landscape page to portrait"),
                _("Use 270° (counterclockwise) for the opposite direction"),
                _("Rotate specific pages if only some pages are misoriented"),
                _(
                    "Check the final PDF before downloading to ensure correct orientation"
                ),
            ],
            "page_content_title": _("Rotate PDF Pages Online - Fix PDF Orientation"),
            "page_content_body": _(
                "<p>Our free PDF rotation tool lets you quickly fix page orientation in any PDF document. "
                "Whether you have scanned documents that came out sideways, or pages that need to be "
                "turned upside down, our tool handles it all.</p>"
                "<p>Choose from 90°, 180°, or 270° rotation angles and apply them to all pages, "
                "just the current page, or specific pages you select. The rotation is instant and "
                "preserves all your content perfectly.</p>"
                "<p>Perfect for fixing scanned documents, rotating landscape pages to portrait, "
                "correcting improperly oriented PDFs, and preparing documents for printing or sharing.</p>"
            ),
        },
    },
    "add_page_numbers": {
        "template": "frontend/pdf_edit/add_page_numbers.html",
        "converter_args": {
            "page_title": _("Add Page Numbers to PDF Online Free | Convertica"),
            "page_description": _(
                "Add page numbers to PDF online free with customizable position, "
                "font size, and format. Fast PDF page numbering tool with no watermark. "
                "Perfect for documents, reports, and academic papers. No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "add page numbers PDF, PDF page numbers, add page numbers to pdf online free, "
                "number pdf pages, pdf page numbering tool, "
                # Position keywords
                "pdf page numbers top, pdf page numbers bottom, "
                "pdf page numbers center, pdf page numbers left, pdf page numbers right, "
                # Use case keywords
                "pdf page numbers for documents, pdf page numbers for reports, "
                "pdf page numbers for academic papers, pdf page numbers for thesis, "
                "pdf page numbering for invoices, pdf page numbers for legal documents, "
                # Feature keywords
                "pdf page numbers custom position, pdf page numbers font size, "
                "pdf page numbers format, add page numbers pdf batch, "
                # Quality keywords
                "add page numbers pdf no watermark, pdf page numbering maintain quality, "
                # Platform keywords
                "add page numbers pdf for mac online, add page numbers pdf for mobile, "
                # Free keywords
                "add page numbers pdf free, add page numbers pdf without registration"
            ),
            "page_subtitle": _("Add page numbers to your PDF in seconds"),
            "header_text": _("Add Page Numbers"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "add_page_numbers_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Add Page Numbers"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Customizable Position"),
                    "description": _(
                        "Place numbers at top, bottom, left, right, or center of pages"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Custom Formatting"),
                    "description": _(
                        "Choose font size, style, and number format to match your document"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Quality Preserved"),
                    "description": _(
                        "Original PDF content and formatting remain unchanged"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Fast Processing"),
                    "description": _("Add page numbers instantly to any PDF document"),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I add page numbers to a PDF?"),
                    "answer": _(
                        "Upload your PDF file, choose where you want the numbers to appear "
                        "(top, bottom, left, right, or center), customize the format if needed, "
                        "and click the button. Your numbered PDF will be ready to download."
                    ),
                },
                {
                    "question": _("Can I choose where page numbers appear?"),
                    "answer": _(
                        "Yes! You can position page numbers at the top or bottom of the page, "
                        "and align them to the left, center, or right. This gives you full control "
                        "over the appearance of your document."
                    ),
                },
                {
                    "question": _(
                        "Will adding page numbers change my document content?"
                    ),
                    "answer": _(
                        "No, adding page numbers only adds the numbers to your pages. "
                        "All existing content, formatting, images, and links remain unchanged."
                    ),
                },
                {
                    "question": _("Can I start numbering from a specific page?"),
                    "answer": _(
                        "Yes, you can customize the starting page number and choose which pages "
                        "to number. This is useful for documents with title pages or table of contents."
                    ),
                },
                {
                    "question": _("What number formats are available?"),
                    "answer": _(
                        "You can use simple numbers (1, 2, 3), Roman numerals (i, ii, iii), "
                        "or custom formats like 'Page 1 of N'. Choose the format that best fits your needs."
                    ),
                },
            ],
            "page_tips": [
                _("Use bottom-center for most documents - it's the standard position"),
                _(
                    "For academic papers, check your institution's formatting requirements"
                ),
                _("Skip the first page if it's a title page or cover"),
                _("Use a smaller font size for page numbers to keep them unobtrusive"),
                _("Preview your document to ensure numbers don't overlap with content"),
            ],
            "page_content_title": _(
                "Add Page Numbers to PDF - Professional Document Numbering"
            ),
            "page_content_body": _(
                "<p>Our free PDF page numbering tool makes it easy to add professional page numbers "
                "to any PDF document. Whether you're preparing a thesis, business report, contract, "
                "or any multi-page document, proper page numbering improves navigation and professionalism.</p>"
                "<p>Customize the position, font size, and format of your page numbers to match your "
                "document's style. You can place numbers at the top or bottom of pages, align them "
                "left, center, or right, and choose from various numbering formats.</p>"
                "<p>Ideal for academic papers, legal documents, business reports, manuals, "
                "and any document that benefits from clear page numbering.</p>"
            ),
        },
    },
    "add_watermark": {
        "template": "frontend/pdf_edit/add_watermark.html",
        "converter_args": {
            "page_title": _("Add Watermark to PDF Online Free | Convertica"),
            "page_description": _(
                "Add watermark to PDF online free with text or image. "
                "Customize position, transparency, and size. "
                "Fast PDF watermarking tool with no watermark on tool itself. "
                "Perfect for document protection and branding. No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "add watermark PDF, PDF watermark, add watermark to pdf online free, "
                "watermark pdf documents, pdf watermarking tool, "
                # Type keywords
                "add text watermark to pdf, add image watermark to pdf, "
                "pdf watermark logo, pdf watermark text, "
                # Customization keywords
                "pdf watermark custom position, pdf watermark transparency, "
                "pdf watermark diagonal, pdf watermark center, "
                # Use case keywords
                "pdf watermark for documents, pdf watermark for protection, "
                "pdf watermark for branding, pdf watermark confidential, "
                # Platform keywords
                "add watermark pdf for mac online, add watermark pdf for mobile, "
                # Free keywords
                "add watermark pdf free, add watermark pdf without registration"
            ),
            "page_subtitle": _("Add watermark to your PDF in seconds"),
            "header_text": _("Add Watermark"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "add_watermark_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Add Watermark"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Text & Image Watermarks"),
                    "description": _(
                        "Add custom text or upload images as watermarks on your PDFs"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Full Customization"),
                    "description": _(
                        "Control color, opacity, size, position, and rotation"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Visual Preview"),
                    "description": _(
                        "See exactly how your watermark will look before applying"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Document Protection"),
                    "description": _("Protect your documents with visible watermarks"),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I add a watermark to a PDF?"),
                    "answer": _(
                        "Upload your PDF, enter text or upload an image, customize appearance, "
                        "position it using the visual editor, and click Add Watermark."
                    ),
                },
                {
                    "question": _("Can I add a logo image as a watermark?"),
                    "answer": _(
                        "Yes! Upload PNG or JPG images as watermarks. Perfect for company logos, "
                        "stamps, or signatures."
                    ),
                },
                {
                    "question": _("How do I make the watermark semi-transparent?"),
                    "answer": _(
                        "Use the opacity slider to adjust transparency from 10%% to 100%%."
                    ),
                },
                {
                    "question": _("Can I add watermark to specific pages only?"),
                    "answer": _(
                        "Yes, apply to all pages, current page, or specify pages like '1,3,5' or '1-5'."
                    ),
                },
                {
                    "question": _("Will the watermark affect document quality?"),
                    "answer": _(
                        "No, watermarks are added as a layer on top of the original content. "
                        "The underlying document quality remains unchanged. You can also remove "
                        "watermarks later if needed."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "Use semi-transparent watermarks (30 to 50 percent opacity) for readability"
                ),
                _("Position diagonal watermarks for document protection"),
                _("Use your company logo for professional branding"),
                _("Add 'CONFIDENTIAL' or 'DRAFT' text for document status"),
                _("Test your watermark on one page before applying to all pages"),
            ],
            "page_content_title": _("Add Watermark to PDF - Protect Your Documents"),
            "page_content_body": _(
                "<p>Our free PDF watermark tool lets you add custom text or image watermarks. "
                "Protect your intellectual property, brand documents, or mark them as confidential.</p>"
                "<p>The visual editor shows exactly how your watermark will appear. "
                "Drag to position, adjust size and rotation - all with real-time preview.</p>"
                "<p><strong>Common uses:</strong> Add company logos for branding, mark documents as "
                "'DRAFT' or 'CONFIDENTIAL', add copyright notices, or include approval stamps "
                "and signatures on official documents.</p>"
            ),
        },
        "extra": {
            "auto_generate_tool_schema": False,
        },
    },
    "crop_pdf": {
        "template": "frontend/pdf_edit/crop_pdf.html",
        "converter_args": {
            "page_title": _("Crop PDF Online Free - Remove Margins | Convertica"),
            "page_description": _(
                "Crop PDF pages online free with precise crop box coordinates. "
                "Fast PDF cropping tool with no watermark, visual editor, "
                "and quality preservation. Perfect for removing margins and "
                "unwanted content. No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "crop PDF, PDF crop, crop pdf online free, "
                "crop pdf pages, pdf cropping tool, "
                # Feature keywords
                "crop pdf with visual editor, crop pdf precise coordinates, "
                "crop pdf remove margins, crop pdf unwanted content, "
                # Use case keywords
                "crop pdf for printing, crop pdf for scanning, "
                "crop pdf for documents, crop pdf trim margins, "
                # Quality keywords
                "crop pdf without losing quality, crop pdf maintain quality, "
                "pdf cropping no watermark, crop pdf high quality, "
                # Platform keywords
                "pdf cropping for mac online, pdf cropping for mobile, "
                # Free keywords
                "crop pdf free, crop pdf without registration"
            ),
            "page_subtitle": _("Crop your PDF pages in seconds"),
            "header_text": _("Crop PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "crop_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Crop PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Visual Crop Editor"),
                    "description": _(
                        "Select crop area visually by clicking and dragging on the PDF"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Quality Preserved"),
                    "description": _(
                        "Crop without any quality loss - content stays sharp"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Apply to Multiple Pages"),
                    "description": _(
                        "Crop all pages, current page, or specific pages at once"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Processing"),
                    "description": _("Fast cropping with immediate download"),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I crop a PDF page?"),
                    "answer": _(
                        "Upload your PDF, click and drag to select the area you want to keep, "
                        "choose which pages to apply the crop to, and click Crop PDF."
                    ),
                },
                {
                    "question": _("Can I crop multiple pages at once?"),
                    "answer": _(
                        "Yes! You can apply the same crop to all pages, just the current page, "
                        "or specify pages like '1,3,5' or '1-5'."
                    ),
                },
                {
                    "question": _("Will cropping reduce PDF quality?"),
                    "answer": _(
                        "No, cropping only removes the area outside the selection. "
                        "The content inside remains at its original quality."
                    ),
                },
                {
                    "question": _("How do I remove margins from a PDF?"),
                    "answer": _(
                        "Upload your PDF and draw a selection box that excludes the margins. "
                        "The areas outside your selection will be removed."
                    ),
                },
                {
                    "question": _("Can I undo a crop after saving?"),
                    "answer": _(
                        "No, cropping permanently removes the areas outside the selection. "
                        "Always keep a backup of your original PDF before cropping. "
                        "You can preview the result before downloading."
                    ),
                },
            ],
            "page_tips": [
                _("Use the corner handles to precisely resize the crop area"),
                _("Drag the selection box to reposition it"),
                _("Apply crop to all pages for consistent margins"),
                _(
                    "Use 'Scale to page size' to fill the entire page with cropped content"
                ),
                _(
                    "Preview the cropped result before downloading to ensure it's correct"
                ),
            ],
            "page_content_title": _("Crop PDF Pages - Remove Margins Online"),
            "page_content_body": _(
                "<p>Our free PDF cropping tool lets you remove unwanted margins, borders, "
                "or content from your PDF pages. The visual editor makes it easy to select "
                "exactly what you want to keep.</p>"
                "<p>Perfect for trimming scanned documents, removing white borders, "
                "or focusing on specific content areas in your PDFs.</p>"
                "<p><strong>Common uses:</strong> Remove scanner margins from scanned documents, "
                "trim white space from exported slides, crop to focus on specific charts or images, "
                "or prepare PDFs for printing with custom page sizes.</p>"
            ),
        },
        "extra": {
            "auto_generate_tool_schema": False,
        },
    },
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
    "pdf_to_excel": {
        "template": "frontend/pdf_convert/pdf_to_excel.html",
        "converter_args": {
            "page_title": _("PDF to Excel - Convertica"),
            "page_description": _(
                "Convert PDF to Excel online free with accurate table extraction. "
                "Extract tables from PDF and convert to XLSX format. "
                "Perfect for invoices, reports, and data analysis. "
                "No registration required."
            ),
            "page_keywords": (
                "PDF to Excel, PDF to XLSX, convert PDF to Excel online free, "
                "pdf to excel without losing formatting, extract tables from pdf to excel, "
                "pdf table to excel converter, pdf to excel converter no email, "
                "pdf to excel fast online, convert pdf spreadsheet to excel, "
                "pdf to xlsx converter online free, pdf to excel converter unlimited, "
                "pdf to excel converter no sign up, convert pdf data to excel, "
                "pdf to excel export free, pdf to excel maintain formatting, "
                "pdf to excel high accuracy, convert pdf invoice to excel, "
                "pdf to excel batch converter, convert multiple pdf to excel online, "
                "pdf to excel no ads, pdf to excel no virus, "
                "pdf to excel converter small file, pdf to excel converter large file, "
                "pdf to excel converter clean layout, pdf to excel converter best 2025, "
                "pdf to excel converter high accuracy, pdf to excel converter for mac online, "
                "pdf to excel for linux online, pdf to excel converter for students, "
                "free pdf to excel tool safe, pdf to excel without registration, "
                "pdf to excel one click, extract pdf table to excel, "
                "pdf to excel keep formatting, pdf to excel high resolution, "
                "pdf to excel for invoices, pdf to excel for reports, "
                "pdf to excel google drive safe, pdf to excel cloud converter, "
                "pdf to excel export data only, pdf data to excel converter, "
                "pdf to excel editor included, pdf to excel converter without errors, "
                "convert pdf spreadsheet to excel, convert pdf data table to excel, "
                "pdf to excel table alignment maintained, pdf to excel for accounting, "
                "pdf to excel for business"
            ),
            "page_subtitle": _("Extract tables from PDF and convert to Excel format"),
            "header_text": _("PDF to Excel Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_excel_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".xlsx",
            "button_text": _("Convert PDF to Excel"),
            "select_file_message": _("Please select a PDF file with tables."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Accurate Table Extraction"),
                    "description": _(
                        "Our advanced AI-powered engine accurately extracts tables from PDF "
                        "documents and converts them to editable Excel spreadsheets with "
                        "preserved cell structure and formatting."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Lightning Fast Conversion"),
                    "description": _(
                        "Convert PDF to Excel in seconds. Our optimized servers process "
                        "your documents quickly so you can start working with your data immediately."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Secure Data Handling"),
                    "description": _(
                        "Your PDF files are processed securely and automatically deleted "
                        "after conversion. We never store or share your sensitive financial data."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Completely Free Service"),
                    "description": _(
                        "Convert PDF to Excel completely free without watermarks, email "
                        "registration, or hidden fees. Perfect for invoices, reports, and financial data."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert a PDF with tables to Excel?"),
                    "answer": _(
                        "Simply upload your PDF file using the button above, then click "
                        "'Convert PDF to Excel'. Our system will automatically detect and extract "
                        "all tables from your PDF and convert them to an editable Excel spreadsheet (XLSX format)."
                    ),
                },
                {
                    "question": _(
                        "Will the table formatting be preserved after conversion?"
                    ),
                    "answer": _(
                        "Yes, our PDF to Excel converter preserves cell structure, borders, and data alignment. "
                        "Merged cells, column widths, and row heights are maintained to give you "
                        "an accurate Excel representation of your PDF tables."
                    ),
                },
                {
                    "question": _("Can I convert scanned PDF documents to Excel?"),
                    "answer": _(
                        "Our converter works best with text-based PDF documents. For scanned PDFs, "
                        "the quality of extraction depends on the scan quality. For best results, "
                        "use PDFs that were created digitally or have clear, high-resolution scans."
                    ),
                },
                {
                    "question": _(
                        "Is there a limit on the number of PDF pages I can convert?"
                    ),
                    "answer": _(
                        "Free users can convert PDF files with a reasonable page limit. For larger "
                        "documents with many tables, consider splitting your PDF into smaller sections "
                        "for optimal conversion quality."
                    ),
                },
                {
                    "question": _("What types of PDFs work best for Excel conversion?"),
                    "answer": _(
                        "PDFs containing structured data like invoices, financial reports, bank statements, "
                        "price lists, inventory sheets, and data tables convert most accurately. "
                        "Documents with complex layouts or images may require manual adjustments."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "For best results, use PDFs with clearly defined table borders and consistent formatting."
                ),
                _(
                    "If your PDF has multiple tables, they will each be placed on separate sheets in Excel."
                ),
                _(
                    "Check the converted Excel file for any cells that may need manual adjustment after conversion."
                ),
                _(
                    "Use PDFs created from spreadsheet applications for the most accurate conversion results."
                ),
                _(
                    "For large PDFs with many pages, consider splitting them before conversion for faster processing."
                ),
            ],
            "page_content_title": _("Professional PDF to Excel Conversion"),
            "page_content_body": _(
                "<p>Converting PDF documents to Excel spreadsheets is essential for modern business "
                "workflows. Whether you're extracting financial data from invoices, analyzing reports, "
                "or importing data from PDF tables into your accounting software, our PDF to Excel "
                "converter makes the process simple and accurate.</p>"
                "<p>Our advanced conversion technology uses intelligent table detection to identify "
                "rows, columns, and cell boundaries in your PDF documents. The extracted data is then "
                "formatted as a proper Excel spreadsheet, ready for editing, calculations, and analysis. "
                "This eliminates hours of manual data entry and reduces the risk of transcription errors.</p>"
                "<p>Perfect for accountants, financial analysts, data entry professionals, and anyone "
                "who needs to work with data locked in PDF format. Convert bank statements, invoices, "
                "purchase orders, inventory lists, and any other tabular PDF documents to editable "
                "Excel files in just a few clicks.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT3M",
        },
    },
    "excel_to_pdf": {
        "template": "frontend/pdf_convert/excel_to_pdf.html",
        "converter_args": {
            "page_title": _("Excel to PDF - Convertica"),
            "page_description": _(
                "Convert Excel to PDF online free with high quality. "
                "Convert XLS and XLSX spreadsheets to PDF format. "
                "Preserve formatting, charts, and formulas. "
                "No registration required."
            ),
            "page_keywords": (
                "Excel to PDF, XLSX to PDF, XLS to PDF, convert Excel to PDF online free, "
                "excel to pdf without losing formatting, excel spreadsheet to pdf, "
                "xlsx to pdf converter no email, excel to pdf fast online, "
                "convert excel workbook to pdf, xlsx to pdf online free, "
                "excel to pdf converter unlimited, excel to pdf converter no sign up, "
                "convert excel data to pdf, excel to pdf export free, "
                "excel to pdf maintain formatting, excel to pdf high quality, "
                "convert excel invoice to pdf, excel to pdf batch converter, "
                "convert multiple excel to pdf online, excel to pdf no ads, "
                "excel to pdf converter best 2025, excel to pdf for business"
            ),
            "page_subtitle": _("Convert Excel spreadsheets to PDF format"),
            "header_text": _("Excel to PDF Converter"),
            "file_input_name": "excel_file",
            "file_accept": ".xls,.xlsx",
            "api_url_name": "excel_to_pdf_api",
            "replace_regex": r"\.(xlsx?|XLSX?)$",
            "replace_to": ".pdf",
            "button_text": _("Convert to PDF"),
            "select_file_message": _("Please select an Excel file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Perfect Formatting Preservation"),
                    "description": _(
                        "Convert Excel spreadsheets to PDF while maintaining all formatting, "
                        "including fonts, colors, borders, merged cells, and column widths. "
                        "Your PDF will look exactly like your Excel file."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Charts & Graphics Support"),
                    "description": _(
                        "All charts, graphs, images, and graphics in your Excel file are "
                        "accurately converted to PDF. Perfect for financial reports and presentations."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Multi-Sheet Conversion"),
                    "description": _(
                        "Excel workbooks with multiple sheets are converted seamlessly. "
                        "Each worksheet becomes a separate section in your PDF document."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Secure & Private"),
                    "description": _(
                        "Your Excel files are processed securely and deleted immediately after conversion. "
                        "No data is stored on our servers. Perfect for confidential business documents."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert Excel to PDF online?"),
                    "answer": _(
                        "Simply upload your Excel file (XLS or XLSX) using the button above, "
                        "then click 'Convert to PDF'. Your spreadsheet will be converted to a "
                        "high-quality PDF file that you can download immediately."
                    ),
                },
                {
                    "question": _("Will my Excel formatting be preserved in the PDF?"),
                    "answer": _(
                        "Yes, our converter preserves all formatting including fonts, colors, borders, "
                        "cell alignment, merged cells, and column widths. Charts, images, and graphics "
                        "are also accurately converted."
                    ),
                },
                {
                    "question": _("Can I convert Excel files with multiple sheets?"),
                    "answer": _(
                        "Yes, Excel workbooks with multiple worksheets are fully supported. "
                        "Each sheet will be converted and included in the final PDF document "
                        "as separate pages or sections."
                    ),
                },
                {
                    "question": _("What Excel formats are supported?"),
                    "answer": _(
                        "We support both XLS (Excel 97-2003) and XLSX (Excel 2007 and later) formats. "
                        "Simply upload your file and it will be converted to PDF automatically."
                    ),
                },
                {
                    "question": _(
                        "Is there a file size limit for Excel to PDF conversion?"
                    ),
                    "answer": _(
                        "Free users can convert Excel files within reasonable size limits. "
                        "For very large spreadsheets with many rows or complex formulas, "
                        "consider splitting them into smaller files for optimal results."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "Set your print area in Excel before converting to control which cells appear in the PDF."
                ),
                _(
                    "Adjust page orientation (portrait/landscape) in Excel for better PDF output."
                ),
                _(
                    "Use 'Fit to Page' settings in Excel to ensure all columns fit on one page width."
                ),
                _(
                    "Remove hidden rows and columns before conversion to reduce PDF file size."
                ),
                _(
                    "Check print preview in Excel to see how your PDF will look before converting."
                ),
            ],
            "page_content_title": _("Convert Excel Spreadsheets to Professional PDFs"),
            "page_content_body": _(
                "<p>Converting Excel spreadsheets to PDF format is essential for sharing financial reports, "
                "invoices, and business documents. PDF ensures your carefully formatted spreadsheets "
                "look identical on any device, without requiring recipients to have Excel installed.</p>"
                "<p>Our Excel to PDF converter handles complex spreadsheets with ease, preserving all "
                "formatting elements including conditional formatting, data bars, charts, and images. "
                "Whether you're converting a simple data table or a complex financial model with "
                "multiple worksheets, the output PDF maintains professional quality.</p>"
                "<p>Perfect for accountants sharing reports with clients, businesses sending invoices, "
                "analysts distributing data summaries, and anyone who needs to convert Excel files "
                "to a universal, non-editable format for secure distribution.</p>"
            ),
        },
    },
    "ppt_to_pdf": {
        "template": "frontend/pdf_convert/ppt_to_pdf.html",
        "converter_args": {
            "page_title": _("PowerPoint to PDF - Convertica"),
            "page_description": _(
                "Convert PowerPoint to PDF online free with high quality. "
                "Convert PPT and PPTX presentations to PDF format. "
                "Preserve slides, animations, and formatting. "
                "No registration required."
            ),
            "page_keywords": (
                "PowerPoint to PDF, PPT to PDF, PPTX to PDF, convert PowerPoint to PDF online free, "
                "ppt to pdf without losing formatting, powerpoint presentation to pdf, "
                "pptx to pdf converter no email, ppt to pdf fast online, "
                "convert powerpoint slides to pdf, pptx to pdf online free, "
                "ppt to pdf converter unlimited, ppt to pdf converter no sign up, "
                "convert presentation to pdf, ppt to pdf export free, "
                "ppt to pdf maintain formatting, ppt to pdf high quality, "
                "convert ppt slides to pdf, ppt to pdf batch converter, "
                "ppt to pdf no ads, ppt to pdf converter best 2025"
            ),
            "page_subtitle": _("Convert PowerPoint presentations to PDF format"),
            "header_text": _("PowerPoint to PDF Converter"),
            "file_input_name": "ppt_file",
            "file_accept": ".ppt,.pptx",
            "api_url_name": "ppt_to_pdf_api",
            "replace_regex": r"\.(pptx?|PPTX?)$",
            "replace_to": ".pdf",
            "button_text": _("Convert to PDF"),
            "select_file_message": _("Please select a PowerPoint file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
                    "gradient": "from-orange-500 to-red-500",
                    "title": _("Slide-Perfect Conversion"),
                    "description": _(
                        "Every slide in your PowerPoint is converted to PDF with pixel-perfect accuracy. "
                        "Fonts, colors, transitions, and layouts are preserved exactly as designed."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Images & Graphics Preserved"),
                    "description": _(
                        "All images, charts, SmartArt, and graphics in your presentation are "
                        "converted with high quality. Perfect for sharing visual presentations."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Speaker Notes Optional"),
                    "description": _(
                        "Convert slides with or without speaker notes. Share clean presentations "
                        "with clients or include notes for detailed documentation."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Instant Conversion"),
                    "description": _(
                        "Convert PowerPoint presentations to PDF in seconds. No software installation "
                        "required - works directly in your browser on any device."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert PowerPoint to PDF online?"),
                    "answer": _(
                        "Upload your PPT or PPTX file using the button above, then click 'Convert to PDF'. "
                        "Your presentation will be converted to a high-quality PDF file that preserves "
                        "all slides, images, and formatting."
                    ),
                },
                {
                    "question": _("Will animations and transitions be preserved?"),
                    "answer": _(
                        "PDF format doesn't support animations or transitions. Each slide will be "
                        "converted as a static page in the PDF. For animated content, consider "
                        "exporting as a video format instead."
                    ),
                },
                {
                    "question": _("Can I convert presentations with embedded videos?"),
                    "answer": _(
                        "Embedded videos cannot be included in PDF files. Video frames will appear "
                        "as static images in the converted PDF. Audio content is also not included "
                        "in PDF output."
                    ),
                },
                {
                    "question": _("What PowerPoint formats are supported?"),
                    "answer": _(
                        "We support both PPT (PowerPoint 97-2003) and PPTX (PowerPoint 2007 and later) "
                        "formats. OpenDocument presentations (ODP) can also be converted."
                    ),
                },
                {
                    "question": _("How can I reduce the PDF file size?"),
                    "answer": _(
                        "Large presentations with many high-resolution images will create larger PDFs. "
                        "To reduce file size, compress images in PowerPoint before converting, or use "
                        "our PDF compression tool after conversion."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "Check your slide master and templates before converting to ensure consistent formatting."
                ),
                _(
                    "Use standard fonts or embed fonts in PowerPoint to avoid font substitution issues."
                ),
                _(
                    "Set your desired slide size in PowerPoint before converting for optimal PDF dimensions."
                ),
                _(
                    "Remove hidden slides before conversion if you don't want them in the PDF."
                ),
                _(
                    "Use high-quality images in your presentation for best results in the PDF."
                ),
            ],
            "page_content_title": _("Convert PowerPoint Presentations to PDF"),
            "page_content_body": _(
                "<p>Converting PowerPoint presentations to PDF format ensures your slides can be viewed "
                "on any device without requiring PowerPoint software. PDF preserves your design, fonts, "
                "and layouts exactly as you created them, making it the preferred format for sharing "
                "presentations with clients, colleagues, or audiences.</p>"
                "<p>Our PowerPoint to PDF converter handles complex presentations with multiple slides, "
                "embedded images, charts, and custom formatting. Whether you're converting a business "
                "proposal, educational lecture, or marketing pitch deck, the output PDF maintains "
                "professional quality and visual fidelity.</p>"
                "<p>Perfect for businesses sharing proposals, educators distributing course materials, "
                "students submitting assignments, and anyone who needs to convert presentations to "
                "a universal format for easy viewing and printing.</p>"
            ),
        },
    },
    "html_to_pdf": {
        "template": "frontend/pdf_convert/html_to_pdf.html",
        "converter_args": {
            "page_title": _("HTML to PDF - Convertica"),
            "page_description": _(
                "Convert HTML to PDF online free with high quality. "
                "Convert HTML content and web pages to PDF format. "
                "Preserve styling, images, and layout. "
                "No registration required."
            ),
            "page_keywords": (
                "HTML to PDF, web page to PDF, URL to PDF, convert HTML to PDF online free, "
                "html to pdf without losing formatting, html content to pdf, "
                "url to pdf converter no email, html to pdf fast online, "
                "convert web page to pdf, html to pdf online free, "
                "html to pdf converter unlimited, html to pdf converter no sign up, "
                "convert html string to pdf, html to pdf export free, "
                "html to pdf maintain styling, html to pdf high quality, "
                "save webpage as pdf, html to pdf batch converter, "
                "html to pdf no ads, html to pdf converter best 2025"
            ),
            "page_subtitle": _("Convert HTML content and web pages to PDF format"),
            "header_text": _("HTML to PDF Converter"),
            "file_input_name": "html_content",
            "file_accept": "",
            "api_url_name": "html_to_pdf_api",
            "replace_regex": r"",
            "replace_to": ".pdf",
            "button_text": _("Convert to PDF"),
            "select_file_message": _("Please enter HTML content or URL."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("URL to PDF Conversion"),
                    "description": _(
                        "Convert any public web page to PDF by simply entering its URL. "
                        "Our service captures the page exactly as it appears in a browser, "
                        "including images, styles, and layout."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("HTML Code to PDF"),
                    "description": _(
                        "Paste your HTML code directly and convert it to PDF. Perfect for "
                        "developers, designers, and anyone working with HTML content that "
                        "needs to be exported as a document."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Customizable Page Settings"),
                    "description": _(
                        "Control page size (A4, Letter, Legal) and margins to get exactly "
                        "the PDF layout you need. Perfect for printing or document archiving."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Fast & Reliable"),
                    "description": _(
                        "Our powerful rendering engine converts HTML and web pages to PDF "
                        "quickly and accurately. CSS, JavaScript, and modern web features are supported."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert a web page URL to PDF?"),
                    "answer": _(
                        "Select the 'URL to PDF' tab, enter the full URL of the web page "
                        "(including https://), customize page settings if needed, then click "
                        "'Convert URL to PDF'. The page will be captured and converted to a downloadable PDF."
                    ),
                },
                {
                    "question": _("Can I convert HTML code directly to PDF?"),
                    "answer": _(
                        "Yes! Select the 'HTML Content' tab and paste your HTML code into the text area. "
                        "You can include CSS styles inline or in <style> tags. Click 'Convert to PDF' "
                        "to generate your PDF document."
                    ),
                },
                {
                    "question": _("Will CSS styles be preserved in the PDF?"),
                    "answer": _(
                        "Yes, CSS styles are fully supported. Inline styles, embedded stylesheets, "
                        "and external CSS (for URL conversion) are all rendered in the PDF. "
                        "Modern CSS features like flexbox and grid are supported."
                    ),
                },
                {
                    "question": _("Can I convert password-protected web pages?"),
                    "answer": _(
                        "Our converter can only access publicly available web pages. Pages that require "
                        "login or authentication cannot be converted. For private content, copy the HTML "
                        "source and use the 'HTML Content' option instead."
                    ),
                },
                {
                    "question": _("What page sizes are available?"),
                    "answer": _(
                        "We support A4, A3, A5, Letter, and Legal page sizes. You can also customize "
                        "margins (top, bottom, left, right) in centimeters to get the exact layout you need."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "For URL conversion, ensure the page is publicly accessible without login requirements."
                ),
                _(
                    "When converting HTML, include all CSS styles inline or in <style> tags for best results."
                ),
                _(
                    "Use print-friendly CSS media queries in your HTML for optimal PDF output."
                ),
                _(
                    "Adjust margins to leave space for binding if you plan to print the PDF."
                ),
                _(
                    "Test with a simple page first to understand how your content will be rendered."
                ),
            ],
            "page_content_title": _("Convert HTML and Web Pages to PDF Documents"),
            "page_content_body": _(
                "<p>Converting HTML content and web pages to PDF is essential for archiving, "
                "sharing, and printing web-based information. Whether you need to save an article, "
                "create documentation from a web page, or convert your HTML email templates to PDF, "
                "our converter handles it all.</p>"
                "<p>Our HTML to PDF converter uses a powerful rendering engine that accurately "
                "captures web content including complex layouts, images, fonts, and CSS styling. "
                "The result is a professional PDF document that looks exactly like the original "
                "web page, ready for distribution or printing.</p>"
                "<p>Perfect for developers creating PDF reports from HTML templates, marketers "
                "archiving web campaigns, researchers saving online articles, and anyone who needs "
                "to convert web content to a portable document format.</p>"
            ),
        },
        "extra": {
            "auto_generate_tool_schema": False,
        },
    },
    "pdf_to_ppt": {
        "template": "frontend/pdf_convert/pdf_to_ppt.html",
        "converter_args": {
            "page_title": _("PDF to PowerPoint - Convertica"),
            "page_description": _(
                "Convert PDF to PowerPoint online free with high quality. "
                "Extract PDF pages and convert to PPTX presentation format. "
                "Perfect for creating editable presentations from PDF documents. "
                "No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "PDF to PowerPoint, PDF to PPT, PDF to PPTX, convert PDF to PowerPoint online free, "
                "pdf to ppt converter, pdf to powerpoint converter, pdf slides to pptx, "
                # Feature keywords
                "pdf to ppt keep formatting, pdf to powerpoint editable, pdf to ppt with images, "
                "pdf to ppt maintain layout, convert pdf pages to slides, pdf to ppt high quality, "
                # Use case keywords
                "convert pdf presentation to ppt, pdf report to powerpoint, pdf ebook to slides, "
                "pdf document to presentation, convert lecture pdf to ppt, pdf to ppt for teaching, "
                "pdf to ppt for meeting, convert scanned pdf to powerpoint, "
                # Platform keywords
                "pdf to ppt mac, pdf to ppt windows, pdf to powerpoint online, "
                "pdf to ppt mobile, pdf to ppt iphone, pdf to ppt android, "
                # Free keywords
                "pdf to ppt free, pdf to powerpoint no registration, pdf to ppt no signup, "
                "pdf to pptx no watermark, pdf to powerpoint unlimited, pdf to ppt safe, "
                # Comparison keywords
                "smallpdf pdf to ppt alternative, ilovepdf to powerpoint alternative, "
                "adobe pdf to powerpoint alternative, best pdf to ppt converter 2026"
            ),
            "page_subtitle": _("Convert PDF documents to PowerPoint presentations"),
            "header_text": _("PDF to PowerPoint Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_ppt_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pptx",
            "button_text": _("Convert PDF to PowerPoint"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
                    "gradient": "from-orange-500 to-red-500",
                    "title": _("Page-to-Slide Conversion"),
                    "description": _(
                        "Each page of your PDF is converted to an individual PowerPoint slide. "
                        "Perfect for repurposing PDF documents into editable presentations."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Fully Editable Output"),
                    "description": _(
                        "The resulting PowerPoint presentation is fully editable. Add, remove, "
                        "or modify content, change layouts, and customize your slides as needed."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Images & Graphics Preserved"),
                    "description": _(
                        "All images, charts, and graphics from your PDF are extracted and "
                        "placed on the corresponding PowerPoint slides with high quality."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Quick & Easy"),
                    "description": _(
                        "Convert your PDF to PowerPoint in seconds. No software installation "
                        "required - works directly in your browser on any device."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert a PDF to PowerPoint?"),
                    "answer": _(
                        "Upload your PDF file using the button above, then click 'Convert PDF to PowerPoint'. "
                        "Each page of your PDF will be converted to a PowerPoint slide, preserving images "
                        "and layout as closely as possible."
                    ),
                },
                {
                    "question": _("Will text be editable after conversion?"),
                    "answer": _(
                        "Text is extracted from your PDF and placed in editable text boxes on each slide. "
                        "Some complex layouts may require manual adjustment after conversion. "
                        "Scanned PDFs without embedded text may not have editable text."
                    ),
                },
                {
                    "question": _("Can I convert PDFs with complex layouts?"),
                    "answer": _(
                        "Our converter handles most PDF layouts well. However, very complex layouts "
                        "with overlapping elements may require some manual adjustment in PowerPoint. "
                        "Simple, clean PDF layouts convert most accurately."
                    ),
                },
                {
                    "question": _("What's the maximum PDF size I can convert?"),
                    "answer": _(
                        "Free users can convert PDFs within reasonable page limits. For larger documents, "
                        "consider splitting your PDF into smaller sections before conversion for optimal results."
                    ),
                },
                {
                    "question": _("Is the original PDF modified during conversion?"),
                    "answer": _(
                        "No, your original PDF file is never modified. We create a new PowerPoint "
                        "presentation from your PDF content. Your source file remains unchanged."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "PDFs with clear, simple layouts convert most accurately to PowerPoint slides."
                ),
                _(
                    "For scanned PDFs, ensure good image quality for better text recognition."
                ),
                _(
                    "After conversion, check each slide and adjust text boxes or images as needed."
                ),
                _(
                    "Use the converted presentation as a starting point and customize with PowerPoint's tools."
                ),
                _(
                    "For presentations with many slides, consider converting smaller sections separately."
                ),
            ],
            "page_content_title": _(
                "Convert PDF Documents to Editable PowerPoint Presentations"
            ),
            "page_content_body": _(
                "<p>Converting PDF files to PowerPoint presentations allows you to repurpose existing "
                "documents for meetings, lectures, and presentations. Our PDF to PowerPoint converter "
                "transforms each PDF page into an individual slide, making it easy to edit, annotate, "
                "and present your content.</p>"
                "<p>Whether you have a PDF report that needs to be presented at a meeting, course "
                "materials that need to be converted to slides, or any document that would work better "
                "as a presentation, our converter provides a quick and accurate solution.</p>"
                "<p>Perfect for business professionals preparing presentations, educators creating "
                "lecture materials, students working on projects, and anyone who needs to transform "
                "static PDF documents into dynamic PowerPoint presentations.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT3M",
        },
    },
    "pdf_to_html": {
        "template": "frontend/pdf_convert/pdf_to_html.html",
        "converter_args": {
            "page_title": _("PDF to HTML - Convertica"),
            "page_description": _(
                "Convert PDF to HTML online free with text extraction. "
                "Extract content from PDF and convert to HTML format. "
                "Perfect for web publishing and content management. "
                "No registration required."
            ),
            "page_keywords": (
                # Primary keywords
                "PDF to HTML, convert PDF to HTML online free, pdf to html converter, "
                "pdf to web page, pdf to html with images, extract text from pdf to html, "
                # Feature keywords
                "pdf to html keep formatting, pdf to html responsive, pdf to html embedded images, "
                "pdf to html clean code, pdf to html maintain layout, pdf to html searchable, "
                # Use case keywords
                "pdf to html for website, pdf to html for cms, pdf to html for wordpress, "
                "pdf to html for blog, convert ebook pdf to html, pdf to html for seo, "
                "publish pdf as webpage, pdf content to web, pdf to html for accessibility, "
                # Quality keywords
                "pdf to html high quality, pdf to html accurate, pdf to html best converter, "
                # Platform keywords
                "pdf to html mac, pdf to html windows, pdf to html online, pdf to html mobile, "
                # Free keywords
                "pdf to html free, pdf to html no registration, pdf to html no signup, "
                "pdf to html no watermark, pdf to html unlimited, "
                # Technical keywords
                "pdf to html5, pdf to responsive html, pdf to html css, pdf to semantic html"
            ),
            "page_subtitle": _("Convert PDF documents to HTML format"),
            "header_text": _("PDF to HTML Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_html_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".html",
            "button_text": _("Convert PDF to HTML"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Clean HTML Output"),
                    "description": _(
                        "Convert your PDF to clean, well-structured HTML code. The output "
                        "is ready for web publishing, content management systems, or further editing."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Images Embedded"),
                    "description": _(
                        "Images from your PDF are automatically converted and embedded as base64 "
                        "data URLs, making your HTML file completely self-contained."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Text Extraction"),
                    "description": _(
                        "All text content is extracted from your PDF and properly formatted "
                        "in HTML. Perfect for content migration and web publishing workflows."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Web-Ready Format"),
                    "description": _(
                        "The converted HTML is ready to be published on any website or "
                        "imported into your CMS. Compatible with all modern browsers."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I convert a PDF to HTML?"),
                    "answer": _(
                        "Upload your PDF file using the button above, then click 'Convert PDF to HTML'. "
                        "Your PDF content will be extracted and converted to HTML format, ready for "
                        "download and web publishing."
                    ),
                },
                {
                    "question": _("Will images from my PDF be included in the HTML?"),
                    "answer": _(
                        "Yes, images from your PDF are automatically extracted and embedded in the HTML "
                        "file as base64 data URLs. This means your HTML file is completely self-contained "
                        "and doesn't require separate image files."
                    ),
                },
                {
                    "question": _("Can I edit the HTML after conversion?"),
                    "answer": _(
                        "The converted HTML is standard HTML code that can be opened and edited "
                        "in any text editor or HTML editor. You can modify the content, styling, "
                        "and structure as needed."
                    ),
                },
                {
                    "question": _("Is the HTML compatible with all browsers?"),
                    "answer": _(
                        "Yes, the generated HTML uses standard HTML5 markup that is compatible "
                        "with all modern web browsers including Chrome, Firefox, Safari, and Edge."
                    ),
                },
                {
                    "question": _("Can I use the HTML on my website?"),
                    "answer": _(
                        "Yes, the converted HTML can be directly uploaded to your website or "
                        "imported into content management systems like WordPress, Drupal, or Joomla. "
                        "You may want to add your own CSS styling for better integration."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "For best results, use PDFs with clear text content rather than scanned images."
                ),
                _(
                    "Add your own CSS stylesheet to the HTML for custom styling that matches your website."
                ),
                _(
                    "Check the converted HTML for any formatting that may need manual adjustment."
                ),
                _(
                    "Large PDFs with many images will create larger HTML files due to embedded images."
                ),
                _(
                    "Consider using a code editor with HTML formatting to review and edit the output."
                ),
            ],
            "page_content_title": _("Convert PDF Documents to HTML for Web Publishing"),
            "page_content_body": _(
                "<p>Converting PDF documents to HTML format opens up new possibilities for content "
                "distribution and web publishing. HTML is the standard format for web pages, making "
                "your content accessible to anyone with a web browser.</p>"
                "<p>Our PDF to HTML converter extracts text, images, and basic formatting from your "
                "PDF and generates clean HTML code. This is perfect for migrating content to websites, "
                "creating web-accessible versions of documents, or extracting content for further editing.</p>"
                "<p>Ideal for content managers publishing documents online, developers extracting content "
                "for web applications, and anyone who needs to make PDF content available on the web "
                "in a searchable, accessible format.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT3M",
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
    "protect_pdf": {
        "template": "frontend/pdf_security/protect_pdf.html",
        "converter_args": {
            "page_title": _("Protect PDF with Password - Convertica"),
            "page_description": _(
                "Protect PDF files with password encryption. "
                "Secure your PDF documents with strong password protection."
            ),
            "page_keywords": (
                # Primary keywords
                "protect PDF, PDF password, encrypt PDF, password protect pdf online free, "
                "pdf security, pdf protection, secure pdf, add password to pdf, "
                # Feature keywords
                "encrypt pdf 256 bit, pdf password protection, pdf encryption tool, "
                "lock pdf with password, pdf owner password, pdf user password, "
                # Use case keywords
                "protect pdf for email, secure pdf for sharing, encrypt confidential pdf, "
                "password protect invoice pdf, secure contract pdf, protect legal documents pdf, "
                "encrypt sensitive pdf, protect financial pdf, secure business pdf, "
                # Restriction keywords
                "prevent pdf printing, prevent pdf copying, restrict pdf editing, "
                "disable pdf printing, pdf copy protection, pdf edit restriction, "
                # Platform keywords
                "protect pdf mac, protect pdf windows, encrypt pdf online, "
                "password pdf mobile, secure pdf iphone, protect pdf android, "
                # Free keywords
                "protect pdf free, encrypt pdf no registration, password pdf no signup, "
                "pdf encryption free online, secure pdf no watermark, "
                # Comparison keywords
                "smallpdf protect alternative, ilovepdf encrypt alternative, adobe encrypt alternative"
            ),
            "page_subtitle": _("Secure your PDF documents with password protection"),
            "header_text": _("Protect PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "protect_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Protect PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-red-500 to-red-600",
                    "title": _("Strong Password Encryption"),
                    "description": _(
                        "Protect your PDF with industry-standard AES encryption. "
                        "Your documents are secured with the password you choose, "
                        "preventing unauthorized access."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("User & Owner Passwords"),
                    "description": _(
                        "Set separate passwords for users and owners. Control who can view, "
                        "edit, print, or modify your PDF with different access levels."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Preserve Document Quality"),
                    "description": _(
                        "Password protection doesn't affect your PDF content. All text, "
                        "images, formatting, and document structure remain intact."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Instant Protection"),
                    "description": _(
                        "Protect your PDF in seconds. Simply upload, set your password, "
                        "and download your secured document. No software required."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I protect a PDF with a password?"),
                    "answer": _(
                        "Upload your PDF file, enter a password in the required field, and click "
                        "'Protect PDF'. Your document will be encrypted and can only be opened "
                        "with the password you set."
                    ),
                },
                {
                    "question": _(
                        "What's the difference between user and owner passwords?"
                    ),
                    "answer": _(
                        "The user password is required to open and view the PDF. The owner password "
                        "allows full access including editing, printing, and copying. If you set both, "
                        "users with just the user password have restricted access."
                    ),
                },
                {
                    "question": _("What encryption is used to protect PDFs?"),
                    "answer": _(
                        "We use industry-standard AES (Advanced Encryption Standard) encryption "
                        "to secure your PDF files. This is the same encryption used by banks and "
                        "government agencies."
                    ),
                },
                {
                    "question": _("Can I remove the password protection later?"),
                    "answer": _(
                        "Yes, if you know the password, you can use our 'Unlock PDF' tool to remove "
                        "the password protection from your PDF document at any time."
                    ),
                },
                {
                    "question": _("Will I be able to open the protected PDF?"),
                    "answer": _(
                        "Yes, you can open the protected PDF in any PDF reader (Adobe Reader, Chrome, etc.) "
                        "by entering the password. Make sure to save your password in a safe place!"
                    ),
                },
            ],
            "page_tips": [
                _(
                    "Use a strong password with a mix of letters, numbers, and special characters."
                ),
                _(
                    "Write down or securely store your password - we cannot recover it if you forget."
                ),
                _(
                    "Use different user and owner passwords for more granular access control."
                ),
                _(
                    "Test opening the protected PDF to ensure you remember the password."
                ),
                _(
                    "For highly sensitive documents, consider additional security measures beyond encryption."
                ),
            ],
            "page_content_title": _(
                "Secure Your PDF Documents with Password Protection"
            ),
            "page_content_body": _(
                "<p>Password protecting your PDF documents is essential for maintaining confidentiality "
                "and controlling access to sensitive information. Whether you're sharing financial reports, "
                "legal documents, or personal files, password encryption ensures only authorized people "
                "can access your content.</p>"
                "<p>Our PDF protection tool uses strong AES encryption to secure your documents. "
                "You can set a single password for all access, or configure separate user and owner "
                "passwords to control different levels of access - from viewing only to full editing rights.</p>"
                "<p>Perfect for businesses sharing confidential documents, individuals protecting "
                "personal files, and anyone who needs to control who can access their PDF documents.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT1M",
        },
    },
    "unlock_pdf": {
        "template": "frontend/pdf_security/unlock_pdf.html",
        "converter_args": {
            "page_title": _("Unlock PDF - Remove Password - Convertica"),
            "page_description": _(
                "Unlock PDF online free. "
                "Remove password protection from PDF files with the correct password. "
                "Fast PDF unlock tool with no watermark. "
                "Perfect for accessing protected documents. No registration required."
            ),
            "page_keywords": (
                "unlock PDF, remove PDF password, unlock pdf online free, "
                "decrypt pdf, pdf unlock, pdf password remover, "
                "unlock pdf no watermark, unlock pdf fast, unlock pdf unlimited, "
                "unlock pdf batch, unlock pdf without losing quality, "
                "unlock pdf maintain quality, unlock pdf safe tool, "
                "pdf unlock for mac online, pdf unlock for mobile, "
                "unlock pdf best 2025, unlock pdf high quality, "
                "unlock pdf for documents, unlock pdf for reports, "
                "pdf unlock google drive safe, pdf unlock cloud tool, "
                "unlock pdf editor included, pdf unlock without errors, "
                "unlock pdf all pages, unlock pdf specific pages, "
                "pdf unlock for students, free pdf unlock tool safe, "
                "unlock pdf without registration, pdf unlock one click, "
                "unlock pdf with password, remove pdf password protection, "
                "decrypt pdf file, unlock encrypted pdf, pdf password removal, "
                "unlock protected pdf, remove pdf restrictions, "
                "unlock pdf for invoices, unlock pdf for legal documents"
            ),
            "page_subtitle": _("Remove password protection from your PDF"),
            "header_text": _("Unlock PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "unlock_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Unlock PDF"),
            "select_file_message": _("Please select a password-protected PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Remove Password Protection"),
                    "description": _(
                        "Easily remove password protection from your PDF files. Enter the correct "
                        "password and get an unlocked PDF that can be opened without restrictions."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Secure & Private"),
                    "description": _(
                        "Your PDF files are processed securely. We don't store your documents "
                        "or passwords. Files are automatically deleted after processing."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Preserve Document Quality"),
                    "description": _(
                        "Unlocking doesn't affect your PDF content. All text, images, "
                        "formatting, and document structure remain exactly the same."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Unlocking"),
                    "description": _(
                        "Remove password protection in seconds. Upload your PDF, enter "
                        "the password, and download your unlocked document immediately."
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("How do I unlock a password-protected PDF?"),
                    "answer": _(
                        "Upload your password-protected PDF, enter the correct password in the "
                        "provided field, and click 'Unlock PDF'. The password protection will be "
                        "removed and you can download an unlocked version."
                    ),
                },
                {
                    "question": _("Can I unlock a PDF without knowing the password?"),
                    "answer": _(
                        "No, you must know the correct password to unlock the PDF. This tool removes "
                        "password protection from PDFs when you provide the correct password. "
                        "We cannot bypass or crack PDF passwords."
                    ),
                },
                {
                    "question": _("What types of PDF protection can this tool remove?"),
                    "answer": _(
                        "This tool removes password protection that requires a password to open the PDF. "
                        "Once unlocked, the PDF can be opened, viewed, printed, and edited without "
                        "any restrictions."
                    ),
                },
                {
                    "question": _("Is my PDF and password secure?"),
                    "answer": _(
                        "Yes, your files and passwords are processed securely and are not stored on "
                        "our servers. All data is automatically deleted after processing. We use "
                        "encrypted connections to protect your information."
                    ),
                },
                {
                    "question": _("Will the unlocked PDF work on all devices?"),
                    "answer": _(
                        "Yes, the unlocked PDF is a standard PDF file that can be opened in any "
                        "PDF reader on any device - computers, tablets, and smartphones. "
                        "No special software is required."
                    ),
                },
            ],
            "page_tips": [
                _(
                    "Make sure you have the correct password before attempting to unlock the PDF."
                ),
                _(
                    "If you've forgotten the password, contact the person who created the protected PDF."
                ),
                _(
                    "After unlocking, you can use our Protect PDF tool to set a new password if needed."
                ),
                _(
                    "Unlocked PDFs can be edited, printed, and shared without restrictions."
                ),
                _(
                    "Keep a backup of your original protected PDF in case you need it later."
                ),
            ],
            "page_content_title": _("Remove Password Protection from Your PDF Files"),
            "page_content_body": _(
                "<p>Unlock password-protected PDF files quickly and easily when you have the correct "
                "password. Our PDF unlock tool removes the password requirement, giving you a PDF "
                "that can be opened, edited, and shared without entering a password each time.</p>"
                "<p>This tool is perfect when you have a legitimately protected PDF and want to "
                "remove the password for easier access. Whether you've received protected documents "
                "from colleagues, downloaded secured files, or want to remove protection from your "
                "own PDFs, our tool makes the process simple.</p>"
                "<p>Note: This tool requires you to know the correct password. It does not bypass "
                "or crack password protection - it simply removes the password requirement from "
                "PDFs when you provide the valid password.</p>"
            ),
        },
    },
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
    "flatten_pdf": {
        "template": "frontend/pdf_edit/flatten_pdf.html",
        "converter_args": {
            "page_title": _(
                "Flatten PDF Online Free - Remove Form Fields | Convertica"
            ),
            "page_description": _(
                "Flatten PDF online free by removing interactive form fields, checkboxes, "
                "and annotations. Creates a static, non-editable PDF. No registration required."
            ),
            "page_keywords": (
                "flatten PDF, flatten PDF online free, remove form fields PDF, "
                "PDF flatten tool, remove annotations PDF, make PDF non-editable, "
                "flatten fillable PDF, remove interactive PDF elements, "
                "flatten PDF form, flatten PDF annotations, "
                "flatten PDF free, flatten PDF no registration"
            ),
            "page_subtitle": _(
                "Remove interactive form fields and annotations from your PDF"
            ),
            "header_text": _("Flatten PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "flatten_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".pdf",
            "button_text": _("Flatten PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Remove Form Fields"),
                    "description": _(
                        "Strips all interactive form fields, checkboxes, radio buttons, and text inputs"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Appearance Preserved"),
                    "description": _(
                        "Visual content stays identical - only interactive elements are removed"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Remove Annotations"),
                    "description": _(
                        "Clears comments, highlights, sticky notes, and all other annotations"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Processing"),
                    "description": _("Fast flattening with immediate download"),
                },
            ],
            "page_faq": [
                {
                    "question": _("What does flattening a PDF mean?"),
                    "answer": _(
                        "Flattening a PDF removes all interactive elements such as form fields, "
                        "checkboxes, and annotations, converting them into static content. "
                        "The PDF looks identical but can no longer be filled out or edited."
                    ),
                },
                {
                    "question": _("Why would I need to flatten a PDF?"),
                    "answer": _(
                        "Flattening is useful when sharing forms that have been filled out, "
                        "when you want to prevent further editing, or when sending a PDF to "
                        "a printer or service that does not support interactive elements."
                    ),
                },
                {
                    "question": _("Does flattening change the visual appearance?"),
                    "answer": _(
                        "No. The visual appearance is preserved exactly. Text, images, and "
                        "layout remain unchanged — only the interactive layer is removed."
                    ),
                },
            ],
            "faq_title": _("Flatten PDF FAQ"),
            "page_tips": [
                _(
                    "Fill out all form fields before flattening to lock in the entered values."
                ),
                _(
                    "Use flattening before printing to ensure all content renders correctly."
                ),
                _(
                    "Flatten PDFs before sharing to prevent recipients from modifying form data."
                ),
            ],
            "tips_title": _("Tips for Flattening PDFs"),
            "page_content_title": _(
                "Flatten PDF to remove form fields and annotations"
            ),
            "page_content_body": _(
                "<p><strong>Flatten PDF</strong> converts an interactive PDF into a static document "
                "by permanently embedding all form field values and removing annotation layers. "
                "The result is a clean, non-editable PDF that looks exactly like the original.</p>"
                "<p>This is commonly needed when distributing completed forms, archiving documents, "
                "or preparing PDFs for printing where interactive elements may cause issues.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT1M",
        },
    },
    "sign_pdf": {
        "template": "frontend/pdf_edit/sign_pdf.html",
        "converter_args": {
            "page_title": _(
                "Sign PDF - Add Signature to PDF Online | Convertica Premium"
            ),
            "page_description": _(
                "Add your handwritten signature to any PDF document. Premium feature: upload a PNG signature image, choose position and apply to all pages. Fast and secure."
            ),
            "page_keywords": (
                "sign PDF online free, add signature to PDF, PDF signature tool, "
                "sign PDF no registration, electronic signature PDF, "
                "add image signature to PDF, PDF sign free, "
                "sign PDF online without registration, PDF e-signature, "
                "sign PDF document online, digital signature PDF free"
            ),
            "page_subtitle": _("Add your image signature to any PDF page"),
            "header_text": _("Sign PDF"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "sign_pdf_api",
            "replace_regex": r"\.pdf$",
            "replace_to": "_signed.pdf",
            "button_text": _("Sign PDF"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Image Signature"),
                    "description": _(
                        "Upload any PNG or JPEG image of your handwritten signature and place it precisely on the PDF"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Flexible Placement"),
                    "description": _(
                        "Choose the exact position and page for your signature, or apply it to all pages at once"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Privacy First"),
                    "description": _(
                        "Files are processed in-memory and deleted immediately — your signature is never stored"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Download"),
                    "description": _(
                        "Signed PDF is ready for immediate download with no delays"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("What image formats are accepted for the signature?"),
                    "answer": _(
                        "You can upload a PNG or JPEG image of your handwritten signature. "
                        "PNG with a transparent background works best so the signature blends naturally into the PDF."
                    ),
                },
                {
                    "question": _("Can I sign all pages at once?"),
                    "answer": _(
                        "Yes. Enable the 'Apply to all pages' option and your signature will be stamped "
                        "on every page of the PDF at the same position."
                    ),
                },
                {
                    "question": _("Is this legally binding?"),
                    "answer": _(
                        "This tool adds a visual image signature to the PDF. For legally binding "
                        "electronic signatures with audit trails and certificates, a dedicated "
                        "e-signature service is recommended."
                    ),
                },
            ],
            "faq_title": _("Sign PDF FAQ"),
            "page_tips": [
                _(
                    "Use a PNG image with a transparent background for the cleanest signature result."
                ),
                _(
                    "Increase the signature width for large-format PDFs so it stays visible."
                ),
                _(
                    "Use the 'Apply to all pages' option to stamp every page in a contract at once."
                ),
            ],
            "tips_title": _("Tips for Signing PDFs"),
            "page_content_title": _("Add your signature to a PDF online"),
            "page_content_body": _(
                "<p><strong>Sign PDF</strong> lets you place a handwritten signature image directly "
                "onto any page of a PDF document. Upload your signature as a PNG or JPEG, choose the "
                "position and page, and download the signed PDF in seconds.</p>"
                "<p>No account required. Files are processed securely and deleted immediately after "
                "download. The signed PDF retains all original content and formatting.</p>"
            ),
        },
    },
    "optimize_image": {
        "template": "frontend/image_tools/optimize_image.html",
        "converter_args": {
            "page_title": _(
                "Optimize Image Online Free - Compress JPEG PNG WebP | Convertica"
            ),
            "page_description": _(
                "Compress and optimize images online free. Reduce JPEG, PNG, and WebP file size "
                "without losing quality. Resize by max dimensions. No registration, no watermark."
            ),
            "page_keywords": (
                "optimize image online free, compress image online, reduce image file size, "
                "image optimizer free, compress JPEG online, compress PNG online, compress WebP, "
                "image compression tool, reduce image size without losing quality, "
                "image optimizer no registration, shrink image file size free"
            ),
            "page_subtitle": _("Reduce image file size while preserving quality"),
            "header_text": _("Optimize Image"),
            "file_input_name": "image_file",
            "file_accept": ".jpg,.jpeg,.png,.webp,.gif",
            "api_url_name": "optimize_image_api",
            "replace_regex": r"\.(jpe?g|png|webp|gif)$",
            "replace_to": "_optimized",
            "button_text": _("Optimize Image"),
            "select_file_message": _("Please select an image file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("JPEG, PNG & WebP"),
                    "description": _(
                        "Compress all major image formats with format-appropriate algorithms for maximum savings"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Resize on the Fly"),
                    "description": _(
                        "Optionally cap the maximum width or height while preserving the original aspect ratio"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Quality Control"),
                    "description": _(
                        "Dial in the exact quality level (10-100) to balance file size and visual fidelity"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Download"),
                    "description": _("Optimized image is ready for immediate download"),
                },
            ],
            "page_faq": [
                {
                    "question": _("Which image formats can be optimized?"),
                    "answer": _(
                        "JPEG, PNG, WebP, and GIF files are supported. Each format is compressed "
                        "using the most effective algorithm for that format."
                    ),
                },
                {
                    "question": _("What quality setting should I use?"),
                    "answer": _(
                        "85 is a good default that balances quality and file size. "
                        "For web use, values between 70 and 85 typically give the best results. "
                        "Use 90+ when quality is critical, such as for print assets."
                    ),
                },
                {
                    "question": _("Can I change the output format while optimizing?"),
                    "answer": _(
                        "Yes. You can optionally convert the image to JPEG, PNG, or WebP during optimization. "
                        "Leave the format field empty to keep the original format."
                    ),
                },
            ],
            "faq_title": _("Image Optimization FAQ"),
            "page_tips": [
                _(
                    "Use WebP output for the smallest file sizes when targeting modern web browsers."
                ),
                _(
                    "Set a max width of 1920px for full-screen hero images to avoid serving oversized files."
                ),
                _(
                    "For thumbnails and previews, a quality of 70-75 is usually indistinguishable from the original."
                ),
            ],
            "tips_title": _("Tips for Image Optimization"),
            "page_content_title": _("Compress and optimize images online"),
            "page_content_body": _(
                "<p><strong>Optimize Image</strong> reduces the file size of your images by applying "
                "smart compression while keeping the visual quality you choose. Smaller images load "
                "faster, consume less bandwidth, and improve your website's performance and SEO.</p>"
                "<p>Supports JPEG, PNG, WebP, and GIF. Optionally resize images by setting a maximum "
                "width or height — the aspect ratio is always preserved.</p>"
            ),
        },
    },
    "convert_image": {
        "template": "frontend/image_tools/convert_image.html",
        "converter_args": {
            "page_title": _(
                "Convert Image Format Online Free - JPEG PNG WebP GIF BMP | Convertica"
            ),
            "page_description": _(
                "Convert images between JPEG, PNG, WebP, GIF, BMP, and TIFF online free. "
                "Fast, lossless format conversion with quality control. No registration required."
            ),
            "page_keywords": (
                "convert image format online free, image converter online, "
                "convert JPEG to PNG, convert PNG to WebP, convert image to JPEG, "
                "image format converter free, convert WebP to PNG, convert BMP to JPEG, "
                "online image converter no registration, image format conversion tool"
            ),
            "page_subtitle": _(
                "Convert any image to JPEG, PNG, WebP, GIF, BMP, or TIFF"
            ),
            "header_text": _("Convert Image"),
            "file_input_name": "image_file",
            "file_accept": ".jpg,.jpeg,.png,.webp,.gif,.bmp,.tiff,.tif",
            "api_url_name": "convert_image_api",
            "replace_regex": r"\.(jpe?g|png|webp|gif|bmp|tiff?)$",
            "replace_to": "",
            "button_text": _("Convert Image"),
            "select_file_message": _("Please select an image file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("6 Output Formats"),
                    "description": _(
                        "Convert to JPEG, PNG, WebP, GIF, BMP, or TIFF — all major image formats supported"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Quality Preserved"),
                    "description": _(
                        "Lossless conversion for PNG/BMP/TIFF; adjustable quality for JPEG and WebP"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Wide Input Support"),
                    "description": _(
                        "Accepts JPEG, PNG, WebP, GIF, BMP, and TIFF as input — convert from any to any"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Conversion"),
                    "description": _("Fast format conversion with immediate download"),
                },
            ],
            "page_faq": [
                {
                    "question": _("Which image formats are supported?"),
                    "answer": _(
                        "Input formats: JPEG, PNG, WebP, GIF, BMP, and TIFF. "
                        "Output formats: JPEG, PNG, WebP, GIF, BMP, and TIFF. "
                        "You can convert between any combination of these formats."
                    ),
                },
                {
                    "question": _("Will converting to JPEG reduce image quality?"),
                    "answer": _(
                        "JPEG is a lossy format, so some quality reduction occurs during conversion. "
                        "Use the quality slider to control the trade-off between file size and quality. "
                        "A setting of 90 or above is nearly indistinguishable from the original."
                    ),
                },
                {
                    "question": _("Does converting PNG to WebP keep transparency?"),
                    "answer": _(
                        "Yes. WebP supports transparency, so transparent PNG images convert to WebP "
                        "with the alpha channel preserved. Converting to JPEG will fill transparent "
                        "areas with white."
                    ),
                },
            ],
            "faq_title": _("Image Conversion FAQ"),
            "page_tips": [
                _(
                    "Convert PNG to WebP for the best balance of quality and file size on the web."
                ),
                _(
                    "Use PNG output when transparency must be preserved — it is the only lossless format that supports it (besides WebP)."
                ),
                _(
                    "Convert to TIFF for archiving or print workflows that require the highest fidelity."
                ),
            ],
            "tips_title": _("Tips for Image Conversion"),
            "page_content_title": _("Convert images between formats online"),
            "page_content_body": _(
                "<p><strong>Convert Image</strong> transforms your image files from one format to another "
                "instantly. Whether you need to convert a PNG to WebP for faster web loading, a BMP to JPEG "
                "to reduce file size, or a GIF to PNG for better quality, this tool handles it all.</p>"
                "<p>No software installation required. All conversions happen on the server and your files "
                "are deleted immediately after download.</p>"
            ),
        },
    },
    "pdf_to_text": {
        "template": "frontend/pdf_convert/pdf_to_text.html",
        "converter_args": {
            "page_title": _(
                "PDF to Text Converter - Extract Text from PDF | Convertica Premium"
            ),
            "page_description": _(
                "Extract all text from PDF files as plain .txt. Premium feature: supports page number markers, layout preservation. Free trial available."
            ),
            "page_keywords": (
                "PDF to text, convert PDF to text online free, extract text from PDF, "
                "PDF to TXT, PDF text extractor, PDF to plain text, "
                "extract text from PDF online, PDF to text converter, "
                "PDF text extraction free, convert PDF to TXT no registration"
            ),
            "page_subtitle": _("Extract plain text from your PDF in seconds"),
            "header_text": _("PDF to Text Converter"),
            "file_input_name": "pdf_file",
            "file_accept": ".pdf",
            "api_url_name": "pdf_to_text_api",
            "replace_regex": r"\.pdf$",
            "replace_to": ".txt",
            "button_text": _("Extract Text"),
            "select_file_message": _("Please select a PDF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Plain Text Output"),
                    "description": _(
                        "Extracts all text content from your PDF into a clean, portable .txt file"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>',
                    "gradient": "from-purple-500 to-purple-600",
                    "title": _("Page Number Dividers"),
                    "description": _(
                        "Optionally add page separators so you know where each page begins"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Layout Preservation"),
                    "description": _(
                        "Option to preserve text positioning and column structure from the original"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Instant Extraction"),
                    "description": _("Fast text extraction with immediate download"),
                },
            ],
            "page_faq": [
                {
                    "question": _("What text formats can be extracted from a PDF?"),
                    "answer": _(
                        "All selectable text embedded in the PDF is extracted. Scanned PDFs "
                        "or image-based PDFs without embedded text will produce empty or minimal output."
                    ),
                },
                {
                    "question": _("What does the 'preserve layout' option do?"),
                    "answer": _(
                        "When enabled, the extractor tries to maintain the original text positioning "
                        "and column structure of the PDF. This can help with multi-column documents "
                        "but may add extra whitespace."
                    ),
                },
                {
                    "question": _("Will the output include images or tables?"),
                    "answer": _(
                        "No. Only plain text is extracted. Images are skipped, and table data "
                        "is extracted as plain text rows without formatting."
                    ),
                },
            ],
            "faq_title": _("PDF to Text FAQ"),
            "page_tips": [
                _("Enable page numbers to easily navigate large extracted documents."),
                _(
                    "For multi-column PDFs, try enabling layout preservation for better results."
                ),
                _(
                    "Scanned PDFs require OCR before text extraction — use our PDF to Word tool for that."
                ),
            ],
            "tips_title": _("Tips for PDF Text Extraction"),
            "page_content_title": _("Extract plain text from PDF files"),
            "page_content_body": _(
                "<p><strong>PDF to Text</strong> extraction pulls all embedded text from your PDF "
                "and saves it as a plain UTF-8 encoded .txt file. This is ideal for data processing, "
                "indexing, archiving, or feeding content into other tools.</p>"
                "<p>Text-based PDFs extract cleanly and quickly. For scanned documents, consider "
                "running OCR first to generate selectable text before using this tool.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT1M",
        },
    },
}
