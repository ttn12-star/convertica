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

    // ─── Server sync (premium) ──────────────────────────────────────────
    // localStorage stays the working cache; the full set is pushed after
    // every change and pulled on the dashboard, so presets follow the
    // account across devices. Last write wins.

    function getCsrfToken() {
        // CSRF_COOKIE_HTTPONLY is on — the cookie is unreadable from JS, so
        // take the token from the DOM (same pattern as background-tasks.js).
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input && input.value) return input.value;
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    let pushTimer = null;

    function pushPresets() {
        clearTimeout(pushTimer);
        pushTimer = setTimeout(function () {
            fetch('/api/workflows/', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ presets: getPresets() }),
            }).catch(function () { /* offline/expired session — cache still works */ });
        }, 400);
    }

    const SYNC_FLAG = 'convertica_wf_synced';

    function syncFromServer() {
        fetch('/api/workflows/', { headers: { 'X-CSRFToken': getCsrfToken() } })
            .then(function (response) {
                if (!response.ok) throw new Error('sync unavailable');
                return response.json();
            })
            .then(function (data) {
                const server = Array.isArray(data.presets) ? data.presets : [];
                // Once this browser has synced, the account copy is
                // authoritative — including an empty one (Clear All on
                // another device must not resurrect here).
                if (server.length || localStorage.getItem(SYNC_FLAG)) {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(server.slice(0, MAX_PRESETS)));
                    window.dispatchEvent(new CustomEvent('convertica:workflows-synced'));
                } else if (getPresets().length) {
                    // First device with local presets seeds the account copy.
                    pushPresets();
                }
                localStorage.setItem(SYNC_FLAG, '1');
            })
            .catch(function () { /* non-premium/offline — local-only mode */ });
    }

    function savePresets(presets) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(presets.slice(0, MAX_PRESETS)));
        pushPresets();
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

    window.pushWorkflowPresets = pushPresets;

    window.encodeWorkflowParams = function (params) {
        try {
            return btoa(unescape(encodeURIComponent(JSON.stringify(params))))
                .replace(/\+/g, '-').replace(/\//g, '_');
        } catch (_) {
            return '';
        }
    };

    function boot() {
        initSaveButton();
        applyFromHash();
        // Pull the account copy only where presets are shown/managed.
        if (document.getElementById('workflowsList')) {
            syncFromServer();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
