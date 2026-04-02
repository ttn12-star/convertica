"""PDF security tool configurations (protect and unlock)."""

from django.utils.translation import gettext_lazy as _

PDF_SECURITY_CONFIGS = {
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
}
