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
}
