"""PDF editing tool configurations (rotate, watermark, crop, etc.)."""

from django.utils.translation import gettext_lazy as _

PDF_EDIT_CONFIGS = {
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
}
