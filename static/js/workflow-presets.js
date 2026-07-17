/**
 * Workflow Presets (Premium feature)
 *
 * Lets premium users save the current tool settings as a named preset and
 * reopen the tool with those settings applied. Presets live in localStorage
 * (key convertica_premium_workflows_v1, same store the Saved Workflows
 * dashboard manages) — nothing is sent to the server.
 *
 * - "Save as workflow" button on converter pages serializes #converterForm
 *   controls (selects, checkboxes, radios, text/number inputs; never files).
 * - Opening a preset navigates to toolUrl#wfp=<base64 json>; this script
 *   applies the params on load and cleans the hash.
 *
 * Loaded globally in base.html for premium users only.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'convertica_premium_workflows_v1';
    const MAX_PRESETS = 40;
    const SKIP_NAMES = new Set(['csrfmiddlewaretoken', 'website']);

    function getPresets() {
        try {
            const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY));
            return Array.isArray(parsed) ? parsed : [];
        } catch (_) {
            return [];
        }
    }

    function savePresets(presets) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(presets.slice(0, MAX_PRESETS)));
    }

    // ─── Serialize current form settings ────────────────────────────────

    function collectParams(form) {
        const params = {};
        form.querySelectorAll('select, textarea, input').forEach((el) => {
            if (!el.name || SKIP_NAMES.has(el.name) || el.disabled) return;
            const type = (el.type || '').toLowerCase();
            if (type === 'file' || type === 'hidden' || type === 'password') return;
            if (type === 'checkbox') {
                if (el.checked) params[el.name] = true;
                return;
            }
            if (type === 'radio') {
                if (el.checked) params[el.name] = el.value;
                return;
            }
            if (el.value !== '' && el.value != null) {
                params[el.name] = el.value;
            }
        });
        return params;
    }

    function applyParams(form, params) {
        Object.keys(params).forEach((name) => {
            const value = params[name];
            form.querySelectorAll('[name="' + CSS.escape(name) + '"]').forEach((el) => {
                const type = (el.type || '').toLowerCase();
                if (type === 'file' || type === 'hidden') return;
                if (type === 'checkbox') {
                    if (el.disabled) return;
                    el.checked = value === true || value === 'true';
                } else if (type === 'radio') {
                    el.checked = el.value === value;
                } else {
                    el.value = value;
                }
                // Dependent UI (e.g. OCR language section) listens to these.
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('input', { bubbles: true }));
            });
        });
    }

    // ─── Save button ────────────────────────────────────────────────────

    function initSaveButton() {
        const btn = document.getElementById('saveWorkflowBtn');
        const form = document.getElementById('converterForm');
        if (!btn || !form) return;

        btn.addEventListener('click', function () {
            const promptText = btn.dataset.promptText || 'Preset name:';
            const defaultName = (document.querySelector('h1') || {}).textContent || '';
            const name = window.prompt(promptText, defaultName.trim().slice(0, 80));
            if (!name || !name.trim()) return;

            const presets = getPresets();
            presets.unshift({
                id: String(Date.now()),
                name: name.trim().slice(0, 80),
                toolUrl: window.location.pathname,
                toolLabel: defaultName.trim().slice(0, 80),
                notes: '',
                params: collectParams(form),
                createdAt: Date.now(),
            });
            savePresets(presets);

            const savedText = btn.dataset.savedText || 'Saved';
            const original = btn.textContent;
            btn.textContent = savedText + ' ✓';
            btn.disabled = true;
            setTimeout(function () {
                btn.textContent = original;
                btn.disabled = false;
            }, 2500);
        });
    }

    // ─── Apply preset from URL hash ─────────────────────────────────────

    function applyFromHash() {
        const match = window.location.hash.match(/#wfp=([A-Za-z0-9+/=_-]+)/);
        if (!match) return;
        let params;
        try {
            params = JSON.parse(
                decodeURIComponent(escape(atob(match[1].replace(/-/g, '+').replace(/_/g, '/'))))
            );
        } catch (_) {
            return;
        }
        if (!params || typeof params !== 'object') return;

        const form = document.getElementById('converterForm');
        if (!form) return;
        applyParams(form, params);
        // Drop the hash so refresh/share doesn't re-apply stale settings.
        history.replaceState(null, '', window.location.pathname + window.location.search);
    }

    window.encodeWorkflowParams = function (params) {
        try {
            return btoa(unescape(encodeURIComponent(JSON.stringify(params))))
                .replace(/\+/g, '-').replace(/\//g, '_');
        } catch (_) {
            return '';
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initSaveButton();
            applyFromHash();
        });
    } else {
        initSaveButton();
        applyFromHash();
    }
})();
