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
    "png_to_ico": {
        "template": "frontend/image_tools/image_to_ico.html",
        "converter_args": {
            "page_title": _(
                "PNG to ICO Converter - Convert PNG to Favicon Icon Online Free | Convertica"
            ),
            "page_description": _(
                "Convert PNG images to ICO format online free. Create a favicon.ico from any PNG file "
                "with 16×16, 32×32, and 48×48 pixel sizes embedded in one file. Transparency preserved. "
                "No registration, no watermark."
            ),
            "page_keywords": (
                "png to ico, convert png to ico, png to favicon, create ico from png, "
                "ico converter, favicon converter, png to icon online free, "
                "make favicon from png, png favicon generator, ico file creator"
            ),
            "page_subtitle": _("Create a multi-size favicon.ico from any PNG image"),
            "header_text": _("PNG to ICO"),
            "file_input_name": "image_file",
            "file_accept": ".png",
            "api_url_name": "image_to_ico_api",
            "replace_regex": r"\.png$",
            "replace_to": "",
            "button_text": _("Convert to ICO"),
            "button_class": "bg-amber-600 hover:bg-amber-700 text-white",
            "select_file_message": _("Please select a PNG file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Three Sizes in One File"),
                    "description": _(
                        "Your ICO output embeds 16×16, 32×32, and 48×48 px frames so browsers always "
                        "pick the sharpest size for each context"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-orange-500 to-red-500",
                    "title": _("Transparency Preserved"),
                    "description": _(
                        "Alpha channel from your original PNG is carried through to every frame — "
                        "your icon looks crisp on any background color"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-amber-600",
                    "title": _("Instant Conversion"),
                    "description": _(
                        "Upload your PNG and download the ICO within seconds — no software to install, "
                        "no account required"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/>',
                    "gradient": "from-amber-400 to-orange-500",
                    "title": _("Private & Secure"),
                    "description": _(
                        "Files are processed on the server and deleted immediately after download — "
                        "your images never leave our secure environment"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("What is an ICO file?"),
                    "answer": _(
                        "An ICO file is a special image container used for website favicons and desktop icons. "
                        "Unlike a regular image file, it can store multiple resolutions inside one file so the "
                        "operating system or browser can pick the most appropriate size automatically."
                    ),
                },
                {
                    "question": _("Which sizes are included in the converted ICO?"),
                    "answer": _(
                        "The converter embeds three sizes: 16×16 px (browser tab), 32×32 px (taskbar and "
                        "bookmark icons), and 48×48 px (Windows desktop shortcut). This covers all common "
                        "favicon usage scenarios."
                    ),
                },
                {
                    "question": _("Is transparency kept when converting PNG to ICO?"),
                    "answer": _(
                        "Yes. If your PNG has a transparent background, the alpha channel is preserved in "
                        "every embedded frame. Your favicon will show the correct transparent areas on any "
                        "browser background."
                    ),
                },
                {
                    "question": _("What PNG size should I start with?"),
                    "answer": _(
                        "For best results, upload a square PNG at least 48×48 px. A 256×256 or 512×512 px "
                        "source image gives the downscaling algorithm the most detail to work with and "
                        "produces the sharpest favicon frames."
                    ),
                },
            ],
            "faq_title": _("PNG to ICO FAQ"),
            "page_tips": [
                _(
                    "Start with a square PNG — non-square images are cropped to a square before conversion."
                ),
                _(
                    "Use a 256×256 or 512×512 px source for the sharpest 16 and 32 px favicon frames."
                ),
                _(
                    "Keep transparency in your PNG to get a clean favicon on any browser background color."
                ),
            ],
            "benefits_title": _("Why Use Our PNG to ICO Converter?"),
            "tips_title": _("Tips for PNG to ICO Conversion"),
            "page_content_title": _("Convert PNG images to ICO favicon format online"),
            "page_content_body": _(
                "<p><strong>PNG to ICO</strong> converts your PNG graphic into a proper multi-resolution "
                "favicon.ico file that browsers and operating systems expect. A single ICO file contains "
                "16×16, 32×32, and 48×48 px variants, so your site icon always looks sharp — whether it "
                "appears in a browser tab, the address bar, bookmarks, or a Windows desktop shortcut.</p>"
                "<p>No design software needed. Upload any square PNG, click Convert, and get a "
                "standards-compliant favicon.ico ready to drop into your website's root directory. "
                "Transparency is fully preserved and your file is deleted from our servers immediately "
                "after you download it.</p>"
            ),
        },
    },
    "jpg_to_ico": {
        "template": "frontend/image_tools/image_to_ico.html",
        "converter_args": {
            "page_title": _(
                "JPG to ICO Converter - Convert JPEG to Favicon Icon Online Free | Convertica"
            ),
            "page_description": _(
                "Convert JPG or JPEG images to ICO format online free. Create a favicon.ico with "
                "16×16, 32×32, and 48×48 px frames from any JPEG photo or logo. "
                "No registration, no watermark."
            ),
            "page_keywords": (
                "jpg to ico, jpeg to ico, convert jpg to ico, convert jpeg to ico, "
                "jpg to favicon, jpeg favicon, create ico from jpg, jpg to icon online free, "
                "favicon from photo, ico from jpeg"
            ),
            "page_subtitle": _(
                "Turn any JPEG photo or logo into a crisp website favicon"
            ),
            "header_text": _("JPG to ICO"),
            "file_input_name": "image_file",
            "file_accept": ".jpg,.jpeg",
            "api_url_name": "image_to_ico_api",
            "replace_regex": r"\.jpe?g$",
            "replace_to": "",
            "button_text": _("Convert to ICO"),
            "button_class": "bg-amber-600 hover:bg-amber-700 text-white",
            "select_file_message": _("Please select a JPG or JPEG file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Multi-Size ICO Output"),
                    "description": _(
                        "Generates a single ICO container with 16×16, 32×32, and 48×48 px frames — "
                        "covers every favicon display context in browsers and operating systems"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/>',
                    "gradient": "from-orange-500 to-red-500",
                    "title": _("Smart Downscaling"),
                    "description": _(
                        "High-quality Lanczos resampling produces sharp favicon frames even from "
                        "large JPEG source images"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-yellow-500 to-amber-600",
                    "title": _("Instant & Free"),
                    "description": _(
                        "No account, no payment, no software to install — convert your JPEG favicon "
                        "in seconds"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-amber-400 to-orange-500",
                    "title": _("Safe & Private"),
                    "description": _(
                        "Your JPEG is deleted from our servers the moment you download the ICO file"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("Can I use a JPEG photo as a favicon?"),
                    "answer": _(
                        "Yes, but browsers require the favicon to be in ICO format (or a modern format "
                        "like PNG or SVG declared in the HTML). This tool converts your JPEG into a "
                        "standards-compliant multi-resolution ICO file that every browser accepts."
                    ),
                },
                {
                    "question": _("What sizes does the ICO file contain?"),
                    "answer": _(
                        "The output ICO embeds three frames: 16×16 px for browser tabs, 32×32 px for "
                        "taskbars and bookmarks, and 48×48 px for Windows desktop shortcuts. All three "
                        "are generated from your JPEG automatically."
                    ),
                },
                {
                    "question": _(
                        "JPEG has no transparency — what background will the ICO use?"
                    ),
                    "answer": _(
                        "JPEG files don't support transparency, so the ICO frames will have a solid "
                        "background. If your logo has a white or colored background in the JPEG, that "
                        "background will appear in the favicon. For a transparent favicon, use a PNG "
                        "source instead."
                    ),
                },
            ],
            "faq_title": _("JPG to ICO FAQ"),
            "page_tips": [
                _(
                    "Crop your JPEG to a square before uploading — the converter works best with square images."
                ),
                _(
                    "Use a high-resolution JPEG (at least 256×256 px) for sharp favicon frames at all sizes."
                ),
                _(
                    "If your design has a transparent background, convert your image to PNG first for best results."
                ),
            ],
            "benefits_title": _("Why Use Our JPG to ICO Converter?"),
            "tips_title": _("Tips for JPG to ICO Conversion"),
            "page_content_title": _("Convert JPEG images to ICO favicon format online"),
            "page_content_body": _(
                "<p><strong>JPG to ICO</strong> converts JPEG photos and logos into a properly formatted "
                "favicon.ico file containing 16×16, 32×32, and 48×48 px icon frames. Whether you have a "
                "product photo, brand logo, or any JPEG graphic, you can turn it into a website favicon "
                "in seconds — no design software required.</p>"
                "<p>The converter applies high-quality Lanczos resampling to produce sharp results at "
                "every embedded size. Simply upload your JPEG, click Convert, and download a "
                "standards-compliant ICO file ready to place in your website's root folder. Your source "
                "image is deleted from our servers immediately after the download.</p>"
            ),
        },
    },
    "svg_to_ico": {
        "template": "frontend/image_tools/image_to_ico.html",
        "converter_args": {
            "page_title": _(
                "SVG to ICO Converter - Convert SVG Vector to Favicon ICO Online Free | Convertica"
            ),
            "page_description": _(
                "Convert SVG vector graphics to ICO format online free. Rasterize your SVG logo to "
                "a multi-resolution favicon.ico with crisp 16×16, 32×32, and 48×48 px frames. "
                "No registration required."
            ),
            "page_keywords": (
                "svg to ico, convert svg to ico, svg to favicon, svg favicon generator, "
                "svg to icon online free, vector to ico, svg favicon converter, "
                "create ico from svg, svg to favicon.ico"
            ),
            "page_subtitle": _(
                "Rasterize your SVG vector logo into a pixel-perfect multi-size favicon"
            ),
            "header_text": _("SVG to ICO"),
            "file_input_name": "image_file",
            "file_accept": ".svg",
            "api_url_name": "image_to_ico_api",
            "replace_regex": r"\.svg$",
            "replace_to": "",
            "button_text": _("Convert to ICO"),
            "button_class": "bg-amber-600 hover:bg-amber-700 text-white",
            "select_file_message": _("Please select an SVG file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Vector-Sharp at Every Size"),
                    "description": _(
                        "SVG is resolution-independent, so rasterizing from vector source yields the "
                        "sharpest possible pixels at 16, 32, and 48 px — far better than downscaling a raster image"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-orange-500 to-amber-500",
                    "title": _("Transparency Supported"),
                    "description": _(
                        "SVG graphics with transparent backgrounds produce ICO files with proper alpha "
                        "transparency in every embedded frame"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/>',
                    "gradient": "from-yellow-500 to-orange-500",
                    "title": _("No Raster Source Needed"),
                    "description": _(
                        "Skip the step of exporting a large PNG from your design app — feed the SVG "
                        "directly and get a perfect favicon.ico"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-amber-400 to-red-500",
                    "title": _("Instant & Free"),
                    "description": _(
                        "Browser-based conversion with no account and no software installation required"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("Why is SVG a great source for favicon creation?"),
                    "answer": _(
                        "SVG is a vector format, meaning it stores shapes mathematically at infinite "
                        "resolution. When converting to ICO, the renderer draws each size (16, 32, 48 px) "
                        "directly from the vector outlines, resulting in much cleaner edges than you'd get "
                        "by downscaling a raster PNG."
                    ),
                },
                {
                    "question": _("Which sizes are included in the ICO output?"),
                    "answer": _(
                        "The output ICO contains three frames: 16×16 px (browser tab), 32×32 px "
                        "(taskbar and bookmark icons), and 48×48 px (Windows desktop shortcuts). "
                        "All three are rasterized from the SVG vector source."
                    ),
                },
                {
                    "question": _(
                        "Will the SVG's transparent background be preserved?"
                    ),
                    "answer": _(
                        "Yes. SVG graphics with no background or an explicitly transparent background "
                        "will produce ICO frames with alpha transparency, so the favicon blends naturally "
                        "with any browser tab color."
                    ),
                },
            ],
            "faq_title": _("SVG to ICO FAQ"),
            "page_tips": [
                _(
                    "Use a square SVG viewBox (e.g. 0 0 100 100) to avoid unexpected cropping during rasterization."
                ),
                _(
                    "Remove any outer margin or padding from your SVG so the icon fills the frame edge-to-edge."
                ),
                _(
                    "Keep the design simple — intricate details look muddy at 16×16 px, so test the smallest size."
                ),
            ],
            "benefits_title": _("Why Use Our SVG to ICO Converter?"),
            "tips_title": _("Tips for SVG to ICO Conversion"),
            "page_content_title": _(
                "Convert SVG vector graphics to ICO favicon format online"
            ),
            "page_content_body": _(
                "<p><strong>SVG to ICO</strong> rasterizes your scalable vector graphic directly into a "
                "multi-resolution favicon.ico. Because SVG stores artwork as mathematical shapes rather "
                "than pixels, the converter renders each embedded size — 16×16, 32×32, and 48×48 px — "
                "from the original vector outlines, producing sharper results than downscaling a bitmap "
                "image would.</p>"
                "<p>This is the ideal workflow for designers who already have their brand logo as an SVG: "
                "no need to export a large PNG first. Simply upload the SVG, click Convert, and download "
                "a browser-ready favicon.ico. Transparency is fully preserved and your file is deleted "
                "immediately after download.</p>"
            ),
        },
    },
    "webp_to_ico": {
        "template": "frontend/image_tools/image_to_ico.html",
        "converter_args": {
            "page_title": _(
                "WebP to ICO Converter - Convert WebP to Favicon ICO Online Free | Convertica"
            ),
            "page_description": _(
                "Convert WebP images to ICO format online free. Turn your WebP logo or graphic into "
                "a multi-resolution favicon.ico with 16×16, 32×32, and 48×48 px frames. "
                "Transparency preserved. No registration."
            ),
            "page_keywords": (
                "webp to ico, convert webp to ico, webp to favicon, webp to icon online free, "
                "webp favicon converter, create ico from webp, webp to favicon.ico, "
                "webp favicon generator, ico from webp"
            ),
            "page_subtitle": _(
                "Convert your modern WebP image into a browser-ready multi-size favicon"
            ),
            "header_text": _("WebP to ICO"),
            "file_input_name": "image_file",
            "file_accept": ".webp",
            "api_url_name": "image_to_ico_api",
            "replace_regex": r"\.webp$",
            "replace_to": "",
            "button_text": _("Convert to ICO"),
            "button_class": "bg-amber-600 hover:bg-amber-700 text-white",
            "select_file_message": _("Please select a WebP file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("WebP Transparency Kept"),
                    "description": _(
                        "Lossless and lossy WebP images with alpha channels are converted with full "
                        "transparency support — every ICO frame respects the original alpha"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-orange-500 to-red-500",
                    "title": _("Three Sizes Embedded"),
                    "description": _(
                        "One ICO file, three resolutions: 16×16, 32×32, and 48×48 px — browsers pick "
                        "the right frame automatically"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/>',
                    "gradient": "from-yellow-500 to-amber-600",
                    "title": _("Modern Format, Classic Output"),
                    "description": _(
                        "Convert your cutting-edge WebP graphics to the universally supported ICO "
                        "format that every browser and OS understands"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-amber-400 to-orange-500",
                    "title": _("No Install Required"),
                    "description": _(
                        "Entirely browser-driven workflow — upload, convert, download in seconds "
                        "with no plugins or desktop software"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("Why would I need to convert WebP to ICO?"),
                    "answer": _(
                        "WebP is an excellent format for web images but it is not supported as a favicon "
                        "by all browsers and operating systems. Converting your WebP graphic to ICO ensures "
                        "your favicon displays correctly everywhere — including older browsers and Windows "
                        "desktop shortcuts."
                    ),
                },
                {
                    "question": _("Does the converter support animated WebP?"),
                    "answer": _(
                        "Animated WebP files are supported as input, but only the first frame is used for "
                        "the ICO conversion. ICO files do not support animation."
                    ),
                },
                {
                    "question": _("Is alpha transparency preserved in the ICO output?"),
                    "answer": _(
                        "Yes. Both lossless and lossy WebP images with an alpha channel are decoded "
                        "correctly, and the transparency information is embedded in every frame of the "
                        "output ICO file."
                    ),
                },
            ],
            "faq_title": _("WebP to ICO FAQ"),
            "page_tips": [
                _(
                    "Use a lossless WebP source for the clearest favicon frames — lossy WebP artifacts "
                    "become more visible at small icon sizes."
                ),
                _(
                    "Start with a square WebP image at 256×256 px or larger for the best downscaling results."
                ),
                _(
                    "If your WebP has a transparent background, the ICO will too — great for dark-mode browser tabs."
                ),
            ],
            "benefits_title": _("Why Use Our WebP to ICO Converter?"),
            "tips_title": _("Tips for WebP to ICO Conversion"),
            "page_content_title": _("Convert WebP images to ICO favicon format online"),
            "page_content_body": _(
                "<p><strong>WebP to ICO</strong> converts Google's modern WebP image format into a "
                "standards-compliant favicon.ico file. WebP is widely used for its excellent compression "
                "and transparency support, but the ICO format is still required by many browsers, operating "
                "systems, and site generators when you specify a favicon. This tool bridges that gap in "
                "seconds.</p>"
                "<p>The converter decodes your WebP — including lossless WebP and WebP with alpha "
                "transparency — and embeds three icon sizes (16×16, 32×32, and 48×48 px) into a single "
                "ICO container. Your source file is deleted from our servers immediately after you download "
                "the result.</p>"
            ),
        },
    },
    "generate_favicon": {
        "template": "frontend/image_tools/favicon_generator.html",
        "converter_args": {
            "page_title": _(
                "Favicon Generator - Create Favicon Package with Apple Touch Icon & PWA Icons | Convertica"
            ),
            "page_description": _(
                "Generate a complete favicon package online free: favicon.ico, PNG icons 16–512 px, "
                "apple-touch-icon 180×180, PWA icons 192×192 and 512×512, site.webmanifest, and an "
                "HTML snippet. One upload, instant ZIP download."
            ),
            "page_keywords": (
                "favicon generator, create favicon, favicon.ico generator, favicon package, "
                "apple touch icon generator, site.webmanifest generator, free favicon maker, "
                "pwa icon generator, favicon all sizes, favicon zip download"
            ),
            "page_subtitle": _(
                "One upload — get favicon.ico, all PNG sizes, Apple touch icon, PWA icons, manifest, and HTML snippet"
            ),
            "header_text": _("Favicon Generator"),
            "file_input_name": "image_file",
            "file_accept": ".png,.jpg,.jpeg,.webp,.svg",
            "api_url_name": "generate_favicon_api",
            "replace_regex": r"\.(png|jpe?g|webp|svg)$",
            "replace_to": "_favicon",
            "button_text": _("Generate Favicon Package"),
            "button_class": "bg-amber-600 hover:bg-amber-700 text-white",
            "select_file_message": _(
                "Please select an image file (PNG, JPG, WebP, or SVG)."
            ),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Complete Package in One ZIP"),
                    "description": _(
                        "favicon.ico, PNG icons from 16 to 512 px, apple-touch-icon 180×180, "
                        "PWA icons 192×192 and 512×512, site.webmanifest, and a ready-to-paste HTML snippet — all in one download"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/>',
                    "gradient": "from-orange-500 to-red-500",
                    "title": _("Apple & PWA Ready"),
                    "description": _(
                        "apple-touch-icon at the required 180×180 px and PWA manifest icons at 192×192 and "
                        "512×512 px are included automatically — no extra steps"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
                    "gradient": "from-yellow-500 to-amber-600",
                    "title": _("HTML Snippet Included"),
                    "description": _(
                        "Copy the generated <link> and <meta> tags directly into your HTML <head> — "
                        "no guessing which tags you need"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-amber-400 to-orange-500",
                    "title": _("Any Source Format"),
                    "description": _(
                        "Upload PNG, JPG, WebP, or SVG — SVG sources produce the sharpest results "
                        "because they are rasterized at each size from vector outlines"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _(
                        "What files are included in the favicon ZIP package?"
                    ),
                    "answer": _(
                        "The ZIP contains: favicon.ico (with 16, 32, and 48 px frames), PNG icons at "
                        "16, 32, 48, 64, 96, 128, 180, 192, 256, and 512 px, an apple-touch-icon-180x180.png "
                        "for iOS home screen bookmarks, PWA icons at 192×192 and 512×512 px, a "
                        "site.webmanifest file for Progressive Web Apps, and an HTML snippet with the "
                        "correct <link> and <meta> tags to paste into your <head>."
                    ),
                },
                {
                    "question": _("How do I install the favicon on my website?"),
                    "answer": _(
                        "Extract the ZIP and upload all files to your website's root directory (the same "
                        "folder as your index.html). Then open the included HTML snippet file and paste "
                        "the <link> and <meta> tags inside the <head> section of every page. Most CMS "
                        "platforms like WordPress, Squarespace, and Webflow let you paste custom <head> "
                        "code in their theme or site settings."
                    ),
                },
                {
                    "question": _("Do I really need multiple favicon files?"),
                    "answer": _(
                        "Yes — different platforms use different files. Desktop browsers use favicon.ico, "
                        "Apple devices use the 180×180 PNG when a user adds your site to the home screen, "
                        "Android Chrome and PWAs use the 192×192 and 512×512 PNGs declared in "
                        "site.webmanifest. Providing the complete package ensures your brand icon looks "
                        "correct everywhere."
                    ),
                },
                {
                    "question": _("What image should I upload for the best results?"),
                    "answer": _(
                        "A square SVG or high-resolution PNG (512×512 px or larger) gives the best "
                        "results. The generator scales down from your source, so more detail in the "
                        "original means sharper icons at smaller sizes. Avoid uploading an image that "
                        "is smaller than 512×512 px, as upscaling reduces quality."
                    ),
                },
            ],
            "faq_title": _("Favicon Generator FAQ"),
            "page_tips": [
                _(
                    "Upload a 512×512 px or larger square image for the sharpest icons — smaller or non-square sources are scaled and cropped to fit."
                ),
                _(
                    "Use a simple, bold design: intricate logos become unrecognizable at 16×16 px."
                ),
                _(
                    "Place all generated files in your site's root directory so browsers can find them automatically."
                ),
            ],
            "benefits_title": _("Why Use Our Favicon Generator?"),
            "tips_title": _("Tips for Creating the Perfect Favicon"),
            "page_content_title": _(
                "Generate a complete favicon package for your website"
            ),
            "page_content_body": _(
                "<p><strong>Favicon Generator</strong> creates everything your website needs to display "
                "a professional icon — in one click. Instead of manually creating a dozen different files "
                "for different browsers and devices, upload a single image and receive a ZIP containing "
                "favicon.ico, ten PNG sizes from 16 to 512 px, an apple-touch-icon at the exact 180×180 px "
                "Apple requires, PWA manifest icons at 192×192 and 512×512 px, a ready-made "
                "site.webmanifest, and an HTML snippet you can copy straight into your &lt;head&gt;.</p>"
                "<p>Modern websites need more than a single favicon.ico: iOS home-screen bookmarks use "
                "the apple-touch-icon PNG, Progressive Web Apps read icons from the web manifest, and "
                "high-DPI displays benefit from larger PNG variants. This generator produces the entire "
                "set in seconds, so you never have to guess which files or sizes a particular platform "
                "expects.</p>"
            ),
        },
    },
    "ico_to_png": {
        "template": "frontend/image_tools/ico_to_png.html",
        "converter_args": {
            "page_title": _(
                "ICO to PNG Converter - Extract PNG from ICO File Online Free | Convertica"
            ),
            "page_description": _(
                "Convert ICO files to PNG online free. Extract the largest embedded frame from any "
                "favicon.ico or icon file as a high-quality PNG image. No registration, no watermark."
            ),
            "page_keywords": (
                "ico to png, convert ico to png, extract png from ico, ico to image, "
                "favicon to png, ico file converter, open ico file, ico to png online free, "
                "extract icon png, ico image extractor"
            ),
            "page_subtitle": _("Extract the largest PNG frame from any ICO icon file"),
            "header_text": _("ICO to PNG"),
            "file_input_name": "ico_file",
            "file_accept": ".ico",
            "api_url_name": "ico_to_png_api",
            "replace_regex": r"\.ico$",
            "replace_to": "",
            "button_text": _("Convert to PNG"),
            "button_class": "bg-amber-600 hover:bg-amber-700 text-white",
            "select_file_message": _("Please select an ICO file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
                    "gradient": "from-amber-500 to-orange-600",
                    "title": _("Largest Frame Extracted"),
                    "description": _(
                        "Automatically selects the highest-resolution frame embedded in the ICO, "
                        "giving you the best-quality PNG output available"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-orange-500 to-red-500",
                    "title": _("Transparency Preserved"),
                    "description": _(
                        "ICO alpha channels are decoded correctly so the extracted PNG retains full "
                        "transparency — no white box around your icon"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/>',
                    "gradient": "from-yellow-500 to-amber-600",
                    "title": _("Universal PNG Output"),
                    "description": _(
                        "PNG is supported everywhere — use the extracted image in design tools, "
                        "websites, documents, or social media without compatibility issues"
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
                    "gradient": "from-amber-400 to-orange-500",
                    "title": _("No Software Needed"),
                    "description": _(
                        "Open and convert ICO files directly in your browser — no plugins, "
                        "no download, no account"
                    ),
                },
            ],
            "page_faq": [
                {
                    "question": _("What does ICO to PNG actually do?"),
                    "answer": _(
                        "An ICO file is a container that holds multiple image frames at different "
                        "resolutions (e.g. 16×16, 32×32, 48×48, 256×256 px). This converter reads the "
                        "ICO, finds the largest embedded frame, and exports it as a standard PNG file "
                        "with transparency preserved."
                    ),
                },
                {
                    "question": _("Which frame size will be in the output PNG?"),
                    "answer": _(
                        "The converter extracts the largest frame available in the ICO file. For most "
                        "modern favicons this is 256×256 px or 48×48 px, depending on how the ICO was "
                        "created. The output PNG resolution matches that frame exactly."
                    ),
                },
                {
                    "question": _(
                        "Can I use the extracted PNG to recreate or edit the icon?"
                    ),
                    "answer": _(
                        "Yes. Once you have the PNG you can edit it in any image editor, use it as a "
                        "source image for a new favicon, or place it in a presentation or document. "
                        "Because PNG is lossless, no quality is lost during the extraction."
                    ),
                },
            ],
            "faq_title": _("ICO to PNG FAQ"),
            "page_tips": [
                _(
                    "If the extracted PNG looks small, the ICO may only contain low-resolution frames — "
                    "try finding the original source image instead."
                ),
                _(
                    "Use the extracted PNG as a source to regenerate a full favicon package with our Favicon Generator."
                ),
                _(
                    "Check that the output PNG has transparency before placing it on a colored background — "
                    "most ICO favicons use alpha transparency."
                ),
            ],
            "benefits_title": _("Why Use Our ICO to PNG Converter?"),
            "tips_title": _("Tips for ICO to PNG Conversion"),
            "page_content_title": _("Extract PNG images from ICO icon files online"),
            "page_content_body": _(
                "<p><strong>ICO to PNG</strong> opens an ICO icon file and extracts the largest "
                "embedded frame as a standard PNG image. ICO files are multi-resolution containers "
                "used for website favicons and Windows application icons, but most image editors and "
                "websites don't accept ICO directly. Converting to PNG gives you a universally "
                "compatible image you can use anywhere.</p>"
                "<p>The extractor automatically selects the highest-resolution frame available in the "
                "ICO and preserves full alpha transparency in the output PNG. This is useful when you "
                "need to recover the original artwork from a favicon, resize or re-use an icon in a "
                "design project, or inspect what sizes are stored inside an ICO file. Your ICO file "
                "is deleted from our servers immediately after you download the PNG.</p>"
            ),
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
