"""Archive tool configurations (protect and unlock ZIP)."""

from django.utils.translation import gettext_lazy as _

ARCHIVE_TOOLS_CONFIGS = {
    "protect_zip": {
        "template": "frontend/archive_tools/protect_zip.html",
        "converter_args": {
            "page_title": _(
                "Password Protect ZIP Online Free - Encrypt ZIP with AES-256 | Convertica"
            ),
            "page_description": _(
                "Password-protect a ZIP archive online free with strong AES-256 encryption. "
                "Lock your ZIP so only people with the password can open it. No registration, "
                "no watermark. Open the result with 7-Zip, WinRAR, Keka or any modern archiver."
            ),
            "page_keywords": (
                "password protect zip, encrypt zip, lock zip file, add password to zip, "
                "zip password online free, aes-256 zip encryption, secure zip, protect zip mac, "
                "protect zip windows, encrypt zip no registration, how to password protect a zip, "
                "zip encryption tool, password zip online, secure zip archive, encrypt zip 7zip"
            ),
            "page_subtitle": _("Lock your ZIP archive with a strong AES-256 password"),
            "header_text": _("Password Protect ZIP"),
            "file_input_name": "archive_file",
            "file_accept": ".zip",
            "api_url_name": "protect_zip_api",
            "replace_regex": r"\.zip$",
            "replace_to": ".zip",
            "button_text": _("Protect ZIP"),
            "select_file_message": _("Please select a ZIP file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
                    "gradient": "from-teal-500 to-teal-600",
                    "title": _("Military-Grade AES-256 Encryption"),
                    "description": _(
                        "Your ZIP is re-packed in memory using AES-256, the same standard used "
                        "by banks and governments. Only someone with the exact password can "
                        "extract the contents."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-cyan-500 to-cyan-600",
                    "title": _("No Registration or Watermark"),
                    "description": _(
                        "Protect your ZIP instantly without creating an account. Your files "
                        "are never watermarked or altered in any way other than adding the "
                        "password you choose."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Files Deleted After Download"),
                    "description": _(
                        "Your original and protected archives are processed in memory and "
                        "deleted from our servers immediately after you download the result. "
                        "Your data stays private."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("Works with All Major Archivers"),
                    "description": _(
                        "The encrypted ZIP is compatible with 7-Zip, WinRAR, WinZip, Keka, "
                        "and virtually all modern archivers. Ready to share on any platform "
                        "in seconds."
                    ),
                },
            ],
            "benefits_title": _("Why Protect Your ZIP with Convertica?"),
            "page_faq": [
                {
                    "question": _("How do I password-protect a ZIP file?"),
                    "answer": _(
                        "Upload your ZIP file, enter the password you want to use, and click "
                        "'Protect ZIP'. Convertica re-packages the archive with AES-256 encryption "
                        "and returns a protected ZIP that can only be opened with your password."
                    ),
                },
                {
                    "question": _("Which programs can open an AES-256 encrypted ZIP?"),
                    "answer": _(
                        "AES-256 encrypted ZIPs open correctly in 7-Zip, WinRAR, WinZip, Keka "
                        "(macOS), and most modern archivers. Important: the built-in zip handlers "
                        "in Windows File Explorer and macOS Archive Utility do not support "
                        "AES-256 and will show an error or fail silently. Download the free "
                        "7-Zip (Windows) or Keka (macOS) to open your protected archive."
                    ),
                },
                {
                    "question": _("Can I change the password later?"),
                    "answer": _(
                        "Yes. Use our 'Unlock ZIP' tool to remove the current password (you must "
                        "know it), then come back to 'Protect ZIP' and set a new one. This two-step "
                        "process lets you update the password whenever you need to."
                    ),
                },
                {
                    "question": _("Are my files safe during the process?"),
                    "answer": _(
                        "Yes. Your files are transferred over an encrypted HTTPS connection, "
                        "processed in memory, and deleted from our servers immediately after "
                        "you download the result. We never store, share, or inspect your data."
                    ),
                },
                {
                    "question": _(
                        "What is the difference between AES-256 and ZipCrypto?"
                    ),
                    "answer": _(
                        "ZipCrypto is an older, weaker encryption standard built into the original "
                        "ZIP format — it can be cracked with modern tools. AES-256 is significantly "
                        "stronger and is the current industry standard for secure encryption. "
                        "Convertica always uses AES-256 to protect your archives."
                    ),
                },
            ],
            "faq_title": _("Password Protect ZIP - FAQ"),
            "page_tips": [
                _(
                    "Use a strong password with a mix of uppercase letters, lowercase letters, "
                    "numbers, and special characters for the best security."
                ),
                _(
                    "Store your password in a secure password manager — Convertica cannot "
                    "recover it if you forget it, and neither can anyone else."
                ),
                _(
                    "To open your protected ZIP on Windows or macOS, install the free 7-Zip "
                    "(Windows) or Keka (macOS) — the built-in archive tools do not support "
                    "AES-256 encrypted ZIPs."
                ),
                _(
                    "Test the protected archive by extracting it with the password before "
                    "deleting the original unprotected copy."
                ),
                _(
                    "To change the password later, use 'Unlock ZIP' to remove the old password, "
                    "then 'Protect ZIP' again to set a new one."
                ),
            ],
            "tips_title": _("Tips for Protecting ZIP Files"),
            "page_content_title": _(
                "Password Protect a ZIP Archive Online with AES-256"
            ),
            "page_content_body": _(
                "<p>Adding a password to a ZIP archive is one of the simplest ways to protect "
                "sensitive files before sharing them by email, cloud storage, or messaging apps. "
                "Convertica encrypts your archive with AES-256 — the same algorithm trusted by "
                "financial institutions and security agencies worldwide — so the contents remain "
                "completely private even if the file falls into the wrong hands.</p>"
                "<p>The entire process happens in memory: your files are never written to disk "
                "on our servers, and the protected archive is deleted right after you download it. "
                "No account is required and no watermarks are added.</p>"
                "<p>One important compatibility note: AES-256 encrypted ZIPs are not supported "
                "by the built-in file managers in Windows (File Explorer) or macOS (Archive "
                "Utility). To open the protected archive, the recipient needs a free modern "
                "archiver such as 7-Zip on Windows or Keka on macOS. Both are free to download "
                "and handle AES-256 ZIPs natively. If you need to change the password in the "
                "future, use our Unlock ZIP tool to remove the current password and then "
                "re-protect the archive with a new one.</p>"
            ),
        },
        "extra": {"how_to_time": "PT1M"},
    },
    "unlock_zip": {
        "template": "frontend/archive_tools/unlock_zip.html",
        "converter_args": {
            "page_title": _(
                "Unlock ZIP Online Free - Remove ZIP Password | Convertica"
            ),
            "page_description": _(
                "Remove a password from a ZIP archive online free. Enter the correct password "
                "and get a normal, unencrypted ZIP back in seconds. Supports AES-256 and "
                "ZipCrypto. No registration, no watermark. Files deleted after download."
            ),
            "page_keywords": (
                "unlock zip, remove zip password, decrypt zip, open password protected zip, "
                "zip password remover, unlock zip online free, decrypt zip file, "
                "remove zip encryption, unprotect zip, zip password removal tool, "
                "unlock aes zip, unlock zipcrypto, unlock zip no registration"
            ),
            "page_subtitle": _(
                "Remove the password from your ZIP archive and get a plain unencrypted file"
            ),
            "header_text": _("Unlock ZIP"),
            "file_input_name": "archive_file",
            "file_accept": ".zip",
            "api_url_name": "unlock_zip_api",
            "replace_regex": r"\.zip$",
            "replace_to": ".zip",
            "button_text": _("Unlock ZIP"),
            "select_file_message": _("Please select a password-protected ZIP file."),
        },
        "seo": {
            "page_benefits": [
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/>',
                    "gradient": "from-teal-500 to-teal-600",
                    "title": _("Remove Password in Seconds"),
                    "description": _(
                        "Provide the correct password and Convertica strips the encryption, "
                        "returning a standard unprotected ZIP that any archiver or built-in "
                        "system tool can open without a password."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
                    "gradient": "from-cyan-500 to-cyan-600",
                    "title": _("AES-256 and ZipCrypto Supported"),
                    "description": _(
                        "Works with both modern AES-256 encrypted archives and older ZipCrypto "
                        "protected ZIPs. Whether the archive was created by 7-Zip, WinRAR, "
                        "WinZip, or any other tool, we've got you covered."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
                    "gradient": "from-green-500 to-green-600",
                    "title": _("Files Preserved and Deleted After Download"),
                    "description": _(
                        "All original file contents are preserved exactly. After you download "
                        "the unlocked archive, both the uploaded and output files are "
                        "permanently deleted from our servers."
                    ),
                },
                {
                    "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                    "gradient": "from-blue-500 to-blue-600",
                    "title": _("No Registration Required"),
                    "description": _(
                        "Unlock a password-protected ZIP without signing up for anything. "
                        "Open the page, upload your archive, enter the password, and download "
                        "the unlocked file — that's all."
                    ),
                },
            ],
            "benefits_title": _("Why Unlock Your ZIP with Convertica?"),
            "page_faq": [
                {
                    "question": _("How do I remove the password from a ZIP file?"),
                    "answer": _(
                        "Upload your password-protected ZIP, enter the correct password in the "
                        "field provided, and click 'Unlock ZIP'. Convertica decrypts the archive "
                        "and returns a normal ZIP with no password required to open it."
                    ),
                },
                {
                    "question": _(
                        "Can this tool crack or bypass a ZIP password I don't know?"
                    ),
                    "answer": _(
                        "No. Convertica requires you to know the correct password. This tool "
                        "removes the password requirement from a ZIP when you provide the valid "
                        "password — it does not crack, guess, or bypass unknown passwords. "
                        "If you do not know the password, contact whoever created the archive."
                    ),
                },
                {
                    "question": _(
                        "What encryption types does the Unlock ZIP tool support?"
                    ),
                    "answer": _(
                        "The tool supports both AES-256 (the modern standard used by 7-Zip and "
                        "WinRAR) and ZipCrypto (the older legacy encryption). As long as you "
                        "supply the correct password, both types are unlocked successfully."
                    ),
                },
                {
                    "question": _(
                        "Will my files be safe during the unlocking process?"
                    ),
                    "answer": _(
                        "Yes. Your archive is transferred over an encrypted HTTPS connection, "
                        "processed in memory, and deleted from our servers right after you "
                        "download the result. We never store, share, or inspect your data "
                        "or your password."
                    ),
                },
                {
                    "question": _(
                        "Can I re-protect the ZIP with a different password afterwards?"
                    ),
                    "answer": _(
                        "Absolutely. Once you have the unlocked ZIP, use our 'Protect ZIP' "
                        "tool to add a new AES-256 password of your choice. This two-step "
                        "workflow is the recommended way to change the password on an "
                        "existing encrypted archive."
                    ),
                },
            ],
            "faq_title": _("Unlock ZIP - FAQ"),
            "page_tips": [
                _(
                    "Make sure you have the exact password before uploading — "
                    "Convertica cannot recover or guess passwords."
                ),
                _(
                    "If the wrong password is entered, the tool will return an error. "
                    "Double-check for typos, especially mixed-case letters and special characters."
                ),
                _(
                    "After unlocking, verify the archive opens correctly and all files are intact "
                    "before deleting the original protected copy."
                ),
                _(
                    "To set a new password on the unlocked archive, use the 'Protect ZIP' tool "
                    "right after downloading the unlocked file."
                ),
                _(
                    "Keep a backup of the original password-protected ZIP until you confirm the "
                    "unlocked version contains everything you need."
                ),
            ],
            "tips_title": _("Tips for Unlocking ZIP Files"),
            "page_content_title": _(
                "Remove Password Protection from a ZIP Archive Online"
            ),
            "page_content_body": _(
                "<p>Unlock a password-protected ZIP file quickly and easily when you know the "
                "correct password. Convertica decrypts your archive and returns a plain, "
                "unencrypted ZIP that can be opened by any archiver — including the built-in "
                "tools in Windows File Explorer and macOS Archive Utility — without entering "
                "a password.</p>"
                "<p>The tool supports both the modern AES-256 standard and the older ZipCrypto "
                "format, so it works with archives created by 7-Zip, WinRAR, WinZip, Keka, "
                "and virtually any other archiver. Your files are processed securely over an "
                "encrypted connection and deleted from our servers immediately after download.</p>"
                "<p>Important: this tool requires you to know the correct password. It removes "
                "the password requirement from your archive — it does not crack, brute-force, "
                "or bypass unknown passwords. If you want to change the password on an existing "
                "archive, unlock it here and then use our Protect ZIP tool to apply a new "
                "AES-256 password.</p>"
            ),
        },
        "extra": {"how_to_time": "PT1M"},
    },
}
