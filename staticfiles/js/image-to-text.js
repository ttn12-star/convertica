/**
 * Image to Text (OCR).
 *
 * Extracts text from an uploaded image and renders it inline (with Copy), then
 * offers the result through the SAME shared download card every other tool uses
 * (window.showDownloadButton) for the .txt, plus a premium "Download as Word"
 * (.docx) action. Free users get an upgrade nudge on premium-only actions and
 * on the server's limit responses.
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('converterForm');
    if (!form) return;

    const submitButton = form.querySelector('button[type="submit"]');
    const resultPanel = document.getElementById('ocrResultPanel');
    const resultText = document.getElementById('ocrResultText');
    const emptyState = document.getElementById('ocrEmptyState');
    const counts = document.getElementById('ocrCounts');
    const copyBtn = document.getElementById('ocrCopyBtn');
    const docxBtn = document.getElementById('ocrDocxBtn');
    const langSelect = document.getElementById('ocrLanguageSelect');

    let lastText = '';
    let lastFile = null;

    const loadingContainer = document.createElement('div');
    loadingContainer.id = 'loadingContainer';
    loadingContainer.className = 'hidden mt-6';

    function setFormDisabled(disabled) {
        if (submitButton) {
            submitButton.disabled = disabled;
            submitButton.classList.toggle('opacity-50', disabled);
            submitButton.classList.toggle('cursor-not-allowed', disabled);
        }
    }

    function hideResultAreas() {
        if (resultPanel) resultPanel.classList.add('hidden');
        if (emptyState) emptyState.classList.add('hidden');
        if (window.hideDownload) window.hideDownload('ocrDownloadCard');
    }

    function selectedFile() {
        const fileInput = document.getElementById('fileInput');
        const fileInputDrop = document.getElementById('fileInputDrop');
        const files = (fileInput && fileInput.files && fileInput.files.length > 0)
            ? fileInput.files
            : (fileInputDrop && fileInputDrop.files ? fileInputDrop.files : null);
        return files && files[0] ? files[0] : null;
    }

    function buildFormData(file, outputFormat) {
        const fd = new FormData();
        fd.append(window.FILE_INPUT_NAME || 'image_file', file);
        if (langSelect && langSelect.value) fd.append('language', langSelect.value);
        if (outputFormat) fd.append('output_format', outputFormat);
        const turnstile = document.querySelector('[name="cf-turnstile-response"]');
        if (turnstile && turnstile.value) fd.append('turnstile_token', turnstile.value);
        return fd;
    }

    async function errorMessageFrom(resp) {
        try {
            const data = await resp.json();
            // CAPTCHA can be required mid-session; render a widget on demand so
            // the "complete the CAPTCHA" message is actionable, not a dead end.
            if (data && data.captcha_required && window.ensureTurnstileWidget) {
                window.ensureTurnstileWidget();
            }
            if (data && data.error) return data.error;
        } catch (_) { /* non-JSON body */ }
        return window.ERROR_MESSAGE;
    }

    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function resetAll() {
        const fileInput = document.getElementById('fileInput');
        const fileInputDrop = document.getElementById('fileInputDrop');
        const selectedFileDiv = document.getElementById('selectedFile');
        const fileInfo = document.getElementById('fileInfo');
        if (fileInput) fileInput.value = '';
        if (fileInputDrop) fileInputDrop.value = '';
        if (selectedFileDiv) selectedFileDiv.classList.add('hidden');
        if (fileInfo) fileInfo.classList.remove('hidden');
        hideResultAreas();
        lastText = '';
        lastFile = null;
        setFormDisabled(false);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function renderResult(text) {
        lastText = text;
        if (text.trim() === '') {
            hideResultAreas();
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }
        if (resultText) resultText.value = text;
        if (counts) {
            const words = (text.trim().match(/\S+/g) || []).length;
            const tpl = window.OCR_COUNTS_TPL || '%(words)s words, %(chars)s characters';
            counts.textContent = tpl.replace('%(words)s', words).replace('%(chars)s', text.length);
        }
        if (emptyState) emptyState.classList.add('hidden');
        if (resultPanel) resultPanel.classList.remove('hidden');

        // Same green download card every other tool renders, for the .txt result.
        const txtBlob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        window.showDownloadButton(txtBlob, (lastFile && lastFile.name) || 'image.txt', 'ocrDownloadCard', {
            successTitle: window.OCR_SUCCESS_TITLE,
            successMessage: window.OCR_SUCCESS_MESSAGE,
            downloadButtonText: window.OCR_DOWNLOAD_TXT,
            convertAnotherText: window.OCR_EXTRACT_ANOTHER,
            onConvertAnother: resetAll,
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = selectedFile();
        if (!file) {
            window.showError(window.SELECT_FILE_MESSAGE || 'Please select an image', 'converterResult');
            return;
        }
        lastFile = file;

        hideResultAreas();
        if (!loadingContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(loadingContainer, form.nextSibling);
        }
        window.showLoading('loadingContainer', { showProgress: false });
        setFormDisabled(true);

        try {
            const resp = await fetch(window.API_URL, {
                method: 'POST',
                headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' },
                body: buildFormData(file, 'txt'),
            });
            window.hideLoading('loadingContainer');
            if (!resp.ok) {
                window.showError(await errorMessageFrom(resp), 'converterResult');
                return;
            }
            renderResult(await resp.text());
        } catch (err) {
            window.hideLoading('loadingContainer');
            window.showError((err && err.message) || window.ERROR_MESSAGE, 'converterResult');
        } finally {
            setFormDisabled(false);
        }
    });

    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(lastText);
                const original = copyBtn.textContent;
                copyBtn.textContent = window.OCR_COPY_DONE || 'Copied!';
                setTimeout(() => { copyBtn.textContent = original; }, 1500);
            } catch (_) { /* clipboard unavailable */ }
        });
    }

    if (docxBtn) {
        docxBtn.addEventListener('click', async () => {
            // Free users: Word export is premium — send them to upgrade.
            if (!window.IS_PREMIUM) {
                if (window.PREMIUM_LINK) window.location.href = window.PREMIUM_LINK;
                return;
            }
            if (!lastFile) return;
            const originalLabel = docxBtn.textContent;
            docxBtn.disabled = true;
            try {
                const resp = await fetch(window.API_URL, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' },
                    body: buildFormData(lastFile, 'docx'),
                });
                if (!resp.ok) {
                    window.showError(await errorMessageFrom(resp), 'converterResult');
                    return;
                }
                const blob = await resp.blob();
                const base = (lastFile.name || 'image').replace(/\.[^.]+$/, '') || 'image';
                downloadBlob(blob, `${base}.docx`);
            } catch (err) {
                window.showError((err && err.message) || window.OCR_DOCX_ERROR, 'converterResult');
            } finally {
                docxBtn.disabled = false;
                docxBtn.textContent = originalLabel;
            }
        });
    }
});
