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

// Pull the most specific error out of an API error body. DRF returns
// {error: "...", details: {field: ["message"]}}; the field message (e.g. "Text
// exceeds the maximum length of 10,000 characters. …") is what the user needs,
// so prefer it over the generic top-level string.
function firstDetailMessage(result) {
    if (!result || typeof result !== 'object') return '';
    const details = result.details;
    if (details && typeof details === 'object') {
        for (const val of Object.values(details)) {
            const msg = Array.isArray(val) ? val[0] : val;
            if (msg) return String(msg);
        }
    }
    return result.error || result.text || '';
}

// Preview font stacks mirror the server's FONT_STACKS so the preview matches
// the generated PDF as closely as the browser allows.
const PREVIEW_FONTS = {
    sans: '"Noto Sans", system-ui, sans-serif',
    serif: '"Noto Serif", Georgia, serif',
    mono: '"Noto Sans Mono", "Courier New", monospace',
};

// Physical page + margin sizes (mm) so the preview shows real page proportions
// and a trustworthy page count. Must match the server: page_size A4/Letter and
// MARGIN_PRESETS narrow/normal/wide (1/2/3 cm).
const PAGE_MM = { A4: [210, 297], Letter: [215.9, 279.4] };
const MARGIN_MM = { narrow: 10, normal: 20, wide: 30 };
const PT_TO_MM = 25.4 / 72; // 1pt = 0.3528mm
const MAX_PREVIEW_SHEETS = 30; // cap rendered sheets; the label still shows the true total

class TextToPDFConverter {
    constructor() {
        this.form = document.getElementById('textToPdfForm');
        this.textInput = document.getElementById('textInput');
        this.previewPages = document.getElementById('previewPages');
        this.previewMeasure = document.getElementById('previewMeasure');
        this.pageCount = document.getElementById('pageCount');
        this.charCounter = document.getElementById('charCounter');
        this.progressSection = document.getElementById('progressSection');
        this.progressBar = document.getElementById('progressBar');
        this.progressPercent = document.getElementById('progressPercent');
        this.progressMessage = document.getElementById('progressMessage');
        this.resultSection = document.getElementById('resultSection');
        this.downloadLink = document.getElementById('downloadLink');
        this.convertAnotherBtn = document.getElementById('convertAnother');

        // Every control that changes the rendered layout re-paginates the preview.
        this.controls = [
            'fontFamily', 'fontSize', 'textColor', 'align', 'pageSize', 'margin',
        ].map((id) => document.getElementById(id));

        // Char-limit ladder: anonymous < registered < premium. The real state
        // arrives async from /api/user-info/; defaults keep the anon floor.
        this.isPremium = false;
        this.isAuthenticated = false;
        const limits = window.TEXT2PDF_LIMITS || {};
        this.maxFree = limits.free || 10000;
        this.maxRegistered = limits.registered || this.maxFree;
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
            if (!el) return;
            // <select> fires 'change'; number/color inputs fire 'input'.
            el.addEventListener('input', () => this.updatePreview());
            el.addEventListener('change', () => this.updatePreview());
        });
        // Re-fit the page thumbnails when the column width changes.
        window.addEventListener('resize', () => this.updatePreview());
        this.updatePreview();
    }

    checkPremiumStatus() {
        fetch('/api/user-info/')
            .then((r) => r.json())
            .then((data) => {
                this.isAuthenticated = data.is_authenticated || false;
                this.isPremium = data.is_premium || false;
                this.updateCharCounter();
            })
            .catch(() => { /* keep anonymous defaults */ });
    }

    currentMax() {
        if (this.isPremium) return this.maxPremium;
        if (this.isAuthenticated) return this.maxRegistered;
        return this.maxFree;
    }

    updatePreview() {
        const size = parseInt(document.getElementById('fontSize').value, 10) || 12;
        const fontFamily =
            PREVIEW_FONTS[document.getElementById('fontFamily').value] || PREVIEW_FONTS.sans;
        const color = document.getElementById('textColor').value;
        const align = document.getElementById('align').value;
        const [pwMM, phMM] = PAGE_MM[document.getElementById('pageSize').value] || PAGE_MM.A4;
        const marginMM = MARGIN_MM[document.getElementById('margin').value] ?? 20;
        const text = this.textInput.value;

        // Scale (px per mm) chosen so a full page fits the preview column width;
        // font and page share the scale, so the page count stays accurate.
        const avail = (this.previewPages.clientWidth || 340) * 0.98;
        const pxPerMM = Math.min(avail / pwMM, 2.6);
        const pageW = pwMM * pxPerMM;
        const pageH = phMM * pxPerMM;
        const pad = marginMM * pxPerMM;
        const usableW = pageW - 2 * pad;
        const usableH = pageH - 2 * pad;
        const fontPx = size * PT_TO_MM * pxPerMM;

        // Shared typography for the measurer and every rendered sheet.
        const typo =
            `font-family:${fontFamily};font-size:${fontPx}px;color:${color};` +
            `text-align:${align};line-height:1.5;white-space:pre-wrap;` +
            `word-wrap:break-word;overflow-wrap:break-word;`;

        // Measure total text height at the page's usable width, then paginate.
        const meas = this.previewMeasure;
        meas.style.cssText =
            `position:absolute;visibility:hidden;inset-inline-start:-9999px;top:0;` +
            `width:${usableW}px;${typo}`;
        // textContent (not innerHTML) so pasted markup shows as literal text,
        // matching the server-side html.escape().
        meas.textContent = text || ' ';
        const pages = Math.max(1, Math.ceil(meas.scrollHeight / usableH));

        this.pageCount.textContent = `≈ ${pages} ${t('pages', 'page(s)')}`;

        // Render page-shaped sheets; each shows its slice via a clipped window
        // with the content translated up by one usable-page height.
        const frag = document.createDocumentFragment();
        for (let i = 0; i < Math.min(pages, MAX_PREVIEW_SHEETS); i++) {
            const sheet = document.createElement('div');
            sheet.className = 'bg-white shadow-sm shrink-0';
            sheet.style.cssText =
                `width:${pageW}px;height:${pageH}px;padding:${pad}px;overflow:hidden;`;
            const win = document.createElement('div');
            win.style.cssText = `width:${usableW}px;height:${usableH}px;overflow:hidden;`;
            const content = document.createElement('div');
            content.setAttribute('dir', 'auto');
            content.textContent = text;
            content.style.cssText = `${typo}transform:translateY(${-i * usableH}px);`;
            win.appendChild(content);
            sheet.appendChild(win);
            frag.appendChild(sheet);
        }
        this.previewPages.replaceChildren(frag);
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
            // Clear, actionable message (mirrors the server) instead of a bare
            // "N / MAX" that doesn't say what to do about it.
            const chars = t('chars', 'characters');
            const hint = this.isPremium
                ? ''
                : this.isAuthenticated
                    ? ` ${t('upgradeHint', 'Upgrade to Premium for more.')}`
                    : ` ${t('loginHint', 'Log in or upgrade to Premium for a higher limit.')}`;
            this.showError(
                `${t('tooLong', 'Text is too long')}: ` +
                `${text.length.toLocaleString()} / ${this.currentMax().toLocaleString()} ${chars}.${hint}`
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
                // CAPTCHA can be demanded mid-session (rate-based) on a page that
                // loaded without a widget. Render one so "complete the CAPTCHA" is
                // actionable instead of a dead end (the whole reason this tool used
                // to trap users). The token then rides along on the next submit.
                if (result.captcha_required === true) {
                    this.ensureTurnstileWidget();
                }
                // Prefer the specific field error (e.g. "Text exceeds the maximum
                // length…") over the generic top-level string so the user learns
                // what actually went wrong.
                throw new Error(firstDetailMessage(result) || t('failed', 'Conversion failed'));
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

    // Render a Cloudflare Turnstile widget on demand when the backend signals
    // captcha_required mid-session. Self-contained (this tool's JS is a single
    // manifest-bypass file and doesn't load utils.js); mirrors utils.js's
    // ensureTurnstileWidget. Turnstile injects a cf-turnstile-response hidden
    // input into #turnstile-container, which lives inside the form, so the token
    // is submitted automatically on the next attempt.
    ensureTurnstileWidget() {
        const siteKey = window.TURNSTILE_SITE_KEY || '';
        const container = document.getElementById('turnstile-container');
        if (!siteKey || !container) return;

        // Already rendered — just bring it into view.
        if (container.querySelector('iframe, .cf-turnstile')) {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }

        const doRender = () => {
            if (!window.turnstile || typeof window.turnstile.render !== 'function') return;
            try {
                container.classList.add('my-6');
                window.turnstile.render(container, {
                    sitekey: siteKey,
                    theme: 'light',
                    size: 'normal',
                });
                container.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } catch (e) {
                if (typeof console !== 'undefined' && console.error) {
                    console.error('Turnstile render failed:', e);
                }
            }
        };

        if (window.turnstile && typeof window.turnstile.render === 'function') {
            doRender();
            return;
        }

        // Lazy-load the Turnstile API (explicit render mode) once.
        let script = document.getElementById('cf-turnstile-script');
        if (!script) {
            script = document.createElement('script');
            script.id = 'cf-turnstile-script';
            script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
            script.async = true;
            script.defer = true;
            const nonced = document.querySelector('script[nonce]');
            if (nonced && nonced.nonce) script.nonce = nonced.nonce;
            script.addEventListener('load', doRender, { once: true });
            document.head.appendChild(script);
        } else {
            script.addEventListener('load', doRender, { once: true });
        }
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
