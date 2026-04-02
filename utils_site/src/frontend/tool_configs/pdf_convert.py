"""PDF conversion tool configurations (PDF↔Word, PDF↔Image, PDF↔Office formats)."""

from django.utils.translation import gettext_lazy as _

PDF_CONVERT_CONFIGS = {
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
