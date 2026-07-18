/**
 * Text to PDF converter.
 * Live CSS preview of pasted text + global style options, then POST to the
 * shared HTML->PDF engine and stream the resulting PDF back.
 */

// Localized UI string with English fallback (window.TEXT2PDF_I18N is populated
// by the template via {% trans %}).
function t(key, fallback) {
    return (window.TEXT2PDF_I18N && window.TEXT2PDF_I18N[key]) || fallback;
}

// Preview font stacks mirror the server's FONT_STACKS so the preview matches
// the generated PDF as closely as the browser allows.
const PREVIEW_FONTS = {
    sans: '"Noto Sans", system-ui, sans-serif',
    serif: '"Noto Serif", Georgia, serif',
    mono: '"Noto Sans Mono", "Courier New", monospace',
};

class TextToPDFConverter {
    constructor() {
        this.form = document.getElementById('textToPdfForm');
        this.textInput = document.getElementById('textInput');
        this.preview = document.getElementById('previewPage');
        this.charCounter = document.getElementById('charCounter');
        this.progressSection = document.getElementById('progressSection');
        this.progressBar = document.getElementById('progressBar');
        this.progressPercent = document.getElementById('progressPercent');
        this.progressMessage = document.getElementById('progressMessage');
        this.resultSection = document.getElementById('resultSection');
        this.downloadLink = document.getElementById('downloadLink');
        this.convertAnotherBtn = document.getElementById('convertAnother');

        this.controls = ['fontFamily', 'fontSize', 'textColor', 'align'].map(
            (id) => document.getElementById(id)
        );

        this.isPremium = false;
        const limits = window.TEXT2PDF_LIMITS || {};
        this.maxFree = limits.free || 10000;
        this.maxPremium = limits.premium || 500000;

        this.init();
    }

    init() {
        this.checkPremiumStatus();
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.convertAnotherBtn.addEventListener('click', () => this.resetForm());

        // Live preview + counter
        this.textInput.addEventListener('input', () => this.updatePreview());
        this.controls.forEach((el) => {
            if (el) el.addEventListener('input', () => this.updatePreview());
        });
        this.updatePreview();
    }

    checkPremiumStatus() {
        fetch('/api/user-info/')
            .then((r) => r.json())
            .then((data) => {
                this.isPremium = data.is_premium || false;
                this.updateCharCounter();
            })
            .catch(() => { /* keep free defaults */ });
    }

    currentMax() {
        return this.isPremium ? this.maxPremium : this.maxFree;
    }

    updatePreview() {
        const size = parseInt(document.getElementById('fontSize').value, 10) || 12;
        const font = document.getElementById('fontFamily').value;
        this.preview.style.fontFamily = PREVIEW_FONTS[font] || PREVIEW_FONTS.sans;
        this.preview.style.fontSize = `${size}pt`;
        this.preview.style.color = document.getElementById('textColor').value;
        this.preview.style.textAlign = document.getElementById('align').value;
        // textContent (not innerHTML) so pasted markup shows as literal text,
        // matching the server-side html.escape().
        this.preview.textContent = this.textInput.value;
        this.updateCharCounter();
    }

    updateCharCounter() {
        const count = this.textInput.value.length;
        const max = this.currentMax();
        this.charCounter.textContent =
            `${count.toLocaleString()} / ${max.toLocaleString()} ${t('chars', 'characters')}`;
        this.charCounter.classList.toggle('text-red-500', count > max);
    }

    async handleSubmit(e) {
        e.preventDefault();
        const text = this.textInput.value;
        if (!text.trim()) {
            this.showError(t('noText', 'Please enter some text to convert'));
            return;
        }
        if (text.length > this.currentMax()) {
            this.showError(
                `${text.length.toLocaleString()} / ${this.currentMax().toLocaleString()} ${t('chars', 'characters')}`
            );
            return;
        }

        this.showProgress();
        this.updateProgress(10, t('creating', 'Creating PDF...'));

        const formData = new FormData(this.form);
        try {
            const csrf = this.form.querySelector('[name=csrfmiddlewaretoken]').value;
            const init = await (window.ConvertiaWebToken
                ? window.ConvertiaWebToken.attachToken({
                    method: 'POST', body: formData, headers: { 'X-CSRFToken': csrf },
                  })
                : Promise.resolve({
                    method: 'POST', body: formData, headers: { 'X-CSRFToken': csrf },
                  }));
            const response = await fetch('/api/text-to-pdf/', init);

            if (!response.ok) {
                const result = await response.json().catch(() => ({}));
                throw new Error(result.error || result.text || t('failed', 'Conversion failed'));
            }

            this.updateProgress(50, t('processing', 'Processing PDF...'));
            const blob = await response.blob();

            if (this._lastObjectUrl) window.URL.revokeObjectURL(this._lastObjectUrl);
            const url = window.URL.createObjectURL(blob);
            this._lastObjectUrl = url;

            this.updateProgress(100, t('done', 'Conversion completed!'));
            this.showResult(url);
        } catch (error) {
            this.showError(error.message);
            this.hideProgress();
        }
    }

    showProgress() {
        this.progressSection.classList.remove('hidden');
        this.resultSection.classList.add('hidden');
        this.updateProgress(0, t('starting', 'Starting conversion...'));
        this.form.querySelector('button[type="submit"]').disabled = true;
    }

    updateProgress(percent, message) {
        this.progressBar.style.width = `${percent}%`;
        this.progressPercent.textContent = `${percent}%`;
        this.progressMessage.textContent = message;
    }

    hideProgress() {
        this.progressSection.classList.add('hidden');
        this.form.querySelector('button[type="submit"]').disabled = false;
    }

    showResult(downloadUrl) {
        this.hideProgress();
        this.resultSection.classList.remove('hidden');

        const nameInput = document.getElementById('filename').value.trim() || 'document';
        const filename = nameInput.endsWith('.pdf') ? nameInput : `${nameInput}.pdf`;
        this.downloadLink.href = downloadUrl;
        this.downloadLink.download = filename;

        // Post-conversion rating form (this tool renders its own download UI).
        if (window.RATING_ENABLED && window.renderRatingForm && window._lastFeedbackToken) {
            window.renderRatingForm(this.resultSection, window._lastFeedbackToken);
        }
        window._lastFeedbackToken = null;
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed top-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg z-50';
        errorDiv.innerHTML = `
            <div class="flex items-center space-x-3">
                <svg class="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                    <h3 class="text-sm font-medium text-red-900">Error</h3>
                    <p class="text-sm text-red-700"></p>
                </div>
                <button type="button" class="text-red-500 hover:text-red-700" onclick="this.parentElement.parentElement.remove()">
                    <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>`;
        // Set message as text (not HTML) to avoid injecting server strings as markup.
        errorDiv.querySelector('p').textContent = message;
        document.body.appendChild(errorDiv);
        setTimeout(() => { if (errorDiv.parentElement) errorDiv.remove(); }, 5000);
    }

    resetForm() {
        this.hideProgress();
        this.resultSection.classList.add('hidden');
        this.form.reset();
        this.progressBar.style.width = '0%';
        this.progressPercent.textContent = '0%';
        this.updatePreview();
    }
}

document.addEventListener('DOMContentLoaded', () => new TextToPDFConverter());
