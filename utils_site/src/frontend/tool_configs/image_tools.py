"""Image tool configurations (optimize and convert)."""

from django.utils.translation import gettext_lazy as _

IMAGE_TOOLS_CONFIGS = {
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
            "benefits_title": _("Why Use Our Image Converter?"),
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
    "heic_to_jpg": {
        "template": "frontend/image_tools/heic_to_jpg.html",
        "converter_args": {
            "page_title": _(
                "HEIC to JPG Converter - Convert iPhone HEIC Photos to JPG, PNG, PDF | Convertica Premium"
            ),
            "page_description": _(
                "Convert Apple HEIC and HEIF photos from your iPhone or iPad to JPG, PNG, or PDF online. "
                "Premium feature with batch conversion. Keeps original quality. No watermark."
            ),
            "page_keywords": (
                "HEIC to JPG, HEIC to JPEG, HEIC to PNG, HEIC to PDF, HEIF converter, "
                "convert HEIC online, iPhone photo converter, convert iPhone HEIC to JPG, "
                "open HEIC on Windows, HEIC to JPG batch, HEIC converter free trial, "
                "HEIC to JPG no watermark, premium HEIC converter, "
                "Apple photo format converter, iOS HEIC to JPG online"
            ),
            "page_subtitle": _(
                "Turn iPhone HEIC photos into universally compatible JPG, PNG, or PDF"
            ),
            "header_text": _("HEIC to JPG Converter"),
            "file_input_name": "image_file",
            "file_accept": ".heic,.heif",
            "api_url_name": "convert_heic_api",
            "replace_regex": r"\.(heic|heif)$",
            "replace_to": "_convertica",
            "button_text": _("Convert HEIC"),
            "select_file_message": _("Please select a HEIC or HEIF file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("iPhone & iPad Photos"),
                    "description": _(
                        "Decode the HEIC and HEIF formats that Apple devices use by default — open them anywhere"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-fuchsia-500 to-pink-600",
                    "title": _("3 Output Formats"),
                    "description": _(
                        "Convert to JPG for universal compatibility, PNG for lossless quality, or PDF for printing and sharing"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Batch Conversion"),
                    "description": _(
                        "Upload up to 10 HEIC photos at once and download them as a single ZIP — premium only"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Original Quality"),
                    "description": _(
                        "Premium pipeline preserves every detail — adjustable JPEG quality, fully lossless PNG"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("Why do iPhone photos arrive as HEIC files?"),
                    "answer": _(
                        "Since iOS 11 (2017), Apple devices save photos in the HEIC / HEIF format by default. "
                        "It produces smaller files at the same quality, but most non-Apple software — including "
                        "Windows, older versions of Office, and many websites — cannot open it. Converting "
                        "HEIC to JPG or PNG makes the photo universally viewable."
                    ),
                },
                {
                    "question": _("Should I convert HEIC to JPG, PNG, or PDF?"),
                    "answer": _(
                        "Choose JPG for general use, sharing, and uploads — it is the most universally supported "
                        "photo format. Choose PNG if you need lossless quality with no compression artifacts. "
                        "Choose PDF when you need to print, archive, or email the photo as a document."
                    ),
                },
                {
                    "question": _("Is the HEIC converter free?"),
                    "answer": _(
                        "The HEIC converter is a premium feature. Premium users can convert single files and "
                        "process up to 10 HEIC photos at once in batch mode. Upgrade to Premium to unlock it "
                        "alongside our other advanced tools."
                    ),
                },
            ],
            "faq_title": _("HEIC Converter FAQ"),
            "page_tips": [
                _(
                    "Convert HEIC to JPG when uploading photos to social networks, job-application portals, or older websites."
                ),
                _(
                    "Use PNG output when you need a transparent or pixel-perfect copy — for example, when editing further in a graphics app."
                ),
                _(
                    "Choose PDF to send an iPhone photo as a printable document — handy for receipts, IDs, or scanned paperwork."
                ),
            ],
            "benefits_title": _("Why Use Our HEIC Converter?"),
            "tips_title": _("Tips for Converting HEIC Photos"),
            "page_content_title": _(
                "Convert HEIC and HEIF photos to JPG, PNG, or PDF online"
            ),
            "page_content_body": _(
                "<p><strong>HEIC to JPG</strong> conversion turns the High-Efficiency Image Container files "
                "that iPhones and iPads create by default into formats every device can open. "
                "Apple's HEIC format is excellent for storage but causes friction whenever you need to upload, "
                "email, or print the photo on non-Apple platforms.</p>"
                "<p>This premium tool decodes HEIC and HEIF files and re-encodes them to <strong>JPG</strong> "
                "(maximum compatibility), <strong>PNG</strong> (lossless quality), or <strong>PDF</strong> "
                "(printable document). Quality settings, batch processing of up to 10 files at once, and "
                "ZIP downloads are all included with Premium.</p>"
            ),
        },
        "extra": {
            "how_to_time": "PT1M",
        },
    },
    "image_to_text": {
        "template": "frontend/image_tools/image_to_text.html",
        "converter_args": {
            "page_title": _(
                "Image to Text Online Free - Extract Text from Photos (OCR) | Convertica"
            ),
            "page_description": _(
                "Extract text from images online free with OCR. Convert JPG, PNG, "
                "WebP, HEIC, BMP, TIFF photos and screenshots to editable text. "
                "17 languages, no registration, no watermark."
            ),
            "page_keywords": (
                "image to text, photo to text, jpg to text, png to text, "
                "picture to text, extract text from image, screenshot to text, "
                "scanned document to text, ocr online free, image to text converter, "
                "convert image to text, free ocr"
            ),
            "page_subtitle": _("Extract editable text from any image in seconds"),
            "header_text": _("Image to Text"),
            "file_input_name": "image_file",
            "file_accept": ".jpg,.jpeg,.png,.webp,.gif,.bmp,.tiff,.tif,.heic,.heif",
            "api_url_name": "image_to_text_api",
            "replace_regex": r"\.(jpe?g|png|webp|gif|bmp|tiff?|heic|heif)$",
            "replace_to": ".txt",
            "button_text": _("Extract Text"),
            "select_file_message": _("Please select an image file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-violet-500 to-violet-600",
                    "title": _("Accurate OCR"),
                    "description": _(
                        "Adaptive preprocessing and confidence filtering for clean, readable text"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("17 Languages + Auto"),
                    "description": _(
                        "Recognize text in 17 languages or let auto-detection pick the best match"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Any Image, Even iPhone HEIC"),
                    "description": _(
                        "JPG, PNG, WebP, HEIC, BMP, TIFF, and GIF — including iPhone photos"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("Free & Private"),
                    "description": _(
                        "No registration, no watermark. Files are deleted right after processing"
                    ),
                },
            ],
            "benefits_title": _("Why Use Our Image to Text Converter?"),
            "page_faq": [
                {
                    "question": _("How do I extract text from an image?"),
                    "answer": _(
                        "Upload your image (JPG, PNG, HEIC, etc.), pick the language or leave it on "
                        "Auto, and click Extract Text. The recognized text appears on the page — copy "
                        "it or download it as a .txt file."
                    ),
                },
                {
                    "question": _("Which languages are supported?"),
                    "answer": _(
                        "17 languages including English, Russian, German, French, Spanish, Italian, "
                        "Portuguese, Polish, Turkish, Ukrainian, Hindi, Indonesian, Arabic, Chinese "
                        "(Simplified and Traditional), Japanese, and Korean — plus automatic detection."
                    ),
                },
                {
                    "question": _("Can it read iPhone HEIC photos?"),
                    "answer": _(
                        "Yes. HEIC and HEIF photos from iPhone and iPad are supported directly — no "
                        "need to convert them to JPG first."
                    ),
                },
                {
                    "question": _("Is it really free?"),
                    "answer": _(
                        "Yes, extracting text from a single image is completely free with no "
                        "registration and no watermark."
                    ),
                },
                {
                    "question": _("Why is some text missing or wrong?"),
                    "answer": _(
                        "OCR works best on sharp, high-contrast images. Blurry photos, handwriting, or "
                        "low-resolution scans reduce accuracy. Use a clear, well-lit image and select "
                        "the correct language for the best results."
                    ),
                },
            ],
            "faq_title": _("Image to Text - FAQ"),
            "page_tips": [
                _("Use a sharp, well-lit image — OCR accuracy drops on blurry photos"),
                _("Select the correct language instead of Auto when you know it"),
                _("Crop out backgrounds so only the text remains for cleaner results"),
                _(
                    "For multi-column layouts, expect text in reading order, not columns"
                ),
                _("Scanned documents work best at 300 DPI or higher"),
            ],
            "tips_title": _("Tips for Best Text Recognition"),
            "page_content_title": _("Extract text from images online with OCR"),
            "page_content_body": _(
                "<p><strong>Image to Text</strong> uses OCR (Optical Character Recognition) to turn "
                "photos, screenshots, and scanned documents into editable text. Upload a JPG, PNG, "
                "WebP, HEIC, BMP, TIFF, or GIF and get the text back instantly.</p>"
                "<p>Perfect for copying text from a screenshot, digitizing a receipt or business card, "
                "or pulling a quote out of a photographed page. Recognition supports 17 languages with "
                "automatic detection, and your files are deleted right after processing.</p>"
            ),
        },
    },
}
