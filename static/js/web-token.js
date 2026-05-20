/**
 * Convertica web-token client.
 *
 * Lazily fetches /api/v1/auth/web-token once per page lifecycle (or when
 * the cached token is < 60s from expiry) and exposes helpers that add the
 * Authorization header to fetch / XHR requests.
 *
 * Intentionally UMD/global style — the rest of the codebase uses globals
 * loaded via plain <script> tags without ES-module bundling.
 *
 * Public API (via window.ConvertiaWebToken):
 *   getToken()              → Promise<string>   — the raw JWT
 *   attachToken(init = {})  → Promise<object>   — fetch init dict with
 *                             Authorization: Bearer <jwt> merged in
 */
(function () {
    'use strict';

    let _token = null;
    let _expiresAt = 0;
    let _inflight = null;   // de-duplicate concurrent refresh calls

    async function _refresh() {
        // Turnstile widget is rendered on tool pages via base.html when
        // turnstile_site_key is set.  The response token is in
        // window.turnstileResponse (set by widget callback) OR we call
        // window.turnstile.getResponse() if the Turnstile JS is loaded.
        // Empty string is fine on dev / pages without Turnstile — the
        // backend returns success when no secret is configured.
        //
        // getResponse() throws TurnstileError when called before a widget
        // is rendered into the DOM (race on slow networks, ad-blocker
        // stripping the script, automated tests, CSP refusal). Swallow
        // here so the mint attempt still goes out — the backend cleanly
        // returns 400 turnstile_token required, which the caller can handle.
        let turnstileToken = '';
        try {
            if (window.turnstile && typeof window.turnstile.getResponse === 'function') {
                turnstileToken = window.turnstile.getResponse() || '';
            }
        } catch (e) {
            // No widget rendered yet — fall through to the window global.
        }
        turnstileToken = turnstileToken || window.turnstileResponse || '';

        const scope = [window.toolSlug || '*'];

        const r = await fetch('/api/v1/auth/web-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ turnstile_token: turnstileToken, scope: scope }),
        });

        if (!r.ok) {
            console.warn('[ConvertiaWebToken] fetch failed', r.status);
            throw new Error('web-token fetch failed: ' + r.status);
        }

        const data = await r.json();
        _token = data.token;
        // Refresh 60 s before expiry so callers always get a valid token.
        _expiresAt = Date.now() + (data.expires_in - 60) * 1000;
        return _token;
    }

    /**
     * Returns a valid JWT string, fetching/refreshing as needed.
     * Multiple simultaneous callers share a single in-flight request.
     */
    async function getToken() {
        if (_token && Date.now() < _expiresAt) return _token;
        if (_inflight) return _inflight;
        _inflight = _refresh().finally(function () { _inflight = null; });
        return _inflight;
    }

    /**
     * Returns a copy of `init` with an Authorization: Bearer header merged in.
     * Preserves all existing headers (including X-CSRFToken).
     *
     * Usage:
     *   const init = await window.ConvertiaWebToken.attachToken({
     *       method: 'POST', body: formData
     *   });
     *   const r = await fetch(url, init);
     */
    async function attachToken(init) {
        init = init || {};
        const token = await getToken();
        // Merge into a plain headers object so we don't disturb existing keys.
        const headers = Object.assign({}, init.headers || {});
        headers['Authorization'] = 'Bearer ' + token;
        return Object.assign({}, init, { headers: headers });
    }

    // Expose on window so plain-script files can call it without imports.
    window.ConvertiaWebToken = {
        getToken: getToken,
        attachToken: attachToken,
    };
})();
