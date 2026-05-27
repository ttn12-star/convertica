/**
 * Image to Text (OCR) — uploads an image, receives a text/plain body, and
 * renders it inline with Copy + Download .txt. Does NOT trigger a file download
 * like converter.js. Bound only on the image_to_text page.
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
    const downloadBtn = document.getElementById('ocrDownloadBtn');
    const langSelect = document.getElementById('ocrLanguageSelect');

    let lastText = '';
    let lastFileName = 'extracted-text';

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

    function hidePanels() {
        if (resultPanel) resultPanel.classList.add('hidden');
        if (emptyState) emptyState.classList.add('hidden');
    }

    function renderText(text) {
        lastText = text;
        if (text.trim() === '') {
            hidePanels();
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }
        if (resultText) resultText.value = text;
        if (counts) {
            const words = (text.trim().match(/\S+/g) || []).length;
            const tpl = window.OCR_COUNTS_TPL || '%(words)s words, %(chars)s characters';
            counts.textContent = tpl
                .replace('%(words)s', words)
                .replace('%(chars)s', text.length);
        }
        if (emptyState) emptyState.classList.add('hidden');
        if (resultPanel) resultPanel.classList.remove('hidden');
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const fileInput = document.getElementById('fileInput');
        const fileInputDrop = document.getElementById('fileInputDrop');
        const files = (fileInput?.files && fileInput.files.length > 0)
            ? fileInput.files
            : (fileInputDrop?.files || null);
        const file = files?.[0];

        if (!file) {
            window.showError(window.SELECT_FILE_MESSAGE || 'Please select an image', 'converterResult');
            return;
        }
        lastFileName = (file.name || 'image').replace(/\.[^.]+$/, '') || 'extracted-text';

        hidePanels();
        if (!loadingContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(loadingContainer, form.nextSibling);
        }
        window.showLoading('loadingContainer', { showProgress: false });
        setFormDisabled(true);

        const formData = new FormData();
        formData.append(window.FILE_INPUT_NAME || 'image_file', file);
        if (langSelect && langSelect.value) {
            formData.append('language', langSelect.value);
        }
        const turnstileResponse = document.querySelector('[name="cf-turnstile-response"]');
        if (turnstileResponse && turnstileResponse.value) {
            formData.append('turnstile_token', turnstileResponse.value);
        }

        try {
            const resp = await fetch(window.API_URL, {
                method: 'POST',
                headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' },
                body: formData,
            });
            window.hideLoading('loadingContainer');
            if (!resp.ok) {
                let msg = window.ERROR_MESSAGE;
                try {
                    const data = await resp.json();
                    if (data && data.error) msg = data.error;
                } catch (_) { /* non-JSON error body */ }
                window.showError(msg, 'converterResult');
                return;
            }
            const text = await resp.text();
            renderText(text);
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

    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            const blob = new Blob([lastText], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${lastFileName}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }
});
