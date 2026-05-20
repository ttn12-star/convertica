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

    function _readTurnstileToken() {
        // Read Turnstile response from either the widget JS API or the
        // global set by the widget callback. Both can be absent — most
        // tool pages don't render the widget, so we'll just have nothing
        // to send, and getToken() will skip the mint entirely instead of
        // hitting the backend with an empty token (every such mint became
        // a `v1_web_token rejected` row in admin operationrun logs).
        try {
            if (window.turnstile && typeof window.turnstile.getResponse === 'function') {
                const t = window.turnstile.getResponse();
                if (t) return t;
            }
        } catch (e) {
            // No widget rendered yet — fall through to the window global.
        }
        return window.turnstileResponse || '';
    }

    async function _refresh() {
        const turnstileToken = _readTurnstileToken();
        if (!turnstileToken) {
            // No Turnstile token available — backend would only return 400
            // turnstile_token required, so skip the mint entirely. Caller
            // will fetch without an Authorization header (legacy / session
            // / API key auth paths still cover that case).
            _token = null;
            _expiresAt = 0;
            return null;
        }

        const scope = [window.toolSlug || '*'];

        const r = await fetch('/api/v1/auth/web-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ turnstile_token: turnstileToken, scope: scope }),
        });

        if (!r.ok) {
            console.warn('[ConvertiaWebToken] mint failed', r.status);
            // Best-effort: don't throw — let the caller proceed without a
            // bearer token, the conversion endpoint has other auth paths.
            _token = null;
            _expiresAt = 0;
            return null;
        }

        const data = await r.json();
        _token = data.token;
        // Refresh 60 s before expiry so callers always get a valid token.
        _expiresAt = Date.now() + (data.expires_in - 60) * 1000;
        return _token;
    }

    /**
     * Returns a valid JWT string when one can be minted, or null.
     * Multiple simultaneous callers share a single in-flight request.
     */
    async function getToken() {
        if (_token && Date.now() < _expiresAt) return _token;
        if (_inflight) return _inflight;
        _inflight = _refresh().finally(function () { _inflight = null; });
        return _inflight;
    }

    /**
     * Returns a copy of `init` with an Authorization: Bearer header merged in
     * when a web token is available. If no token can be minted (no Turnstile
     * widget on the page, or mint endpoint refused), the init is returned
     * unchanged so the caller's fetch still goes out — relying on whichever
     * other auth path (session, API key, legacy Referer/captcha cookie) the
     * server side accepts.
     */
    async function attachToken(init) {
        init = init || {};
        let token = null;
        try {
            token = await getToken();
        } catch (e) {
            // Network glitch / unexpected error — fall through.
            token = null;
        }
        if (!token) return init;
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
