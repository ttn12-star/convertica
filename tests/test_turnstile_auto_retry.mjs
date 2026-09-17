// Smallest check that fails if the automatic CAPTCHA recovery regresses.
// Loads the real static/js/utils.js into a stubbed browser and drives the fetch
// interceptor it installs. Guards what a broken refactor would silently lose:
//   1. a rejected upload is replayed automatically, with the token attached, so
//      the visitor never has to notice the widget or press the button again;
//   2. the challenge is requested in interaction-only mode (nothing to click);
//   3. requests that are not uploads are passed through untouched;
//   4. automatic replays are capped, so a request that keeps coming back as
//      captcha_required cannot bounce solve -> replay forever.
import assert from 'node:assert';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(root, 'static/js/utils.js'), 'utf8');

const CAPTCHA_BODY = JSON.stringify({ error: 'CAPTCHA verification required.', captcha_required: true });

let rendered = null;
const calls = [];

const container = {
    classList: { add() {} },
    querySelector: () => null,
    scrollIntoView() {},
};

// Answers 400/captcha_required until a token rides along, then 200.
function backend(_input, init) {
    const body = init && init.body;
    const token = body && typeof body.get === 'function' ? body.get('turnstile_token') : null;
    calls.push(token);
    return Promise.resolve(token
        ? new Response('PDF', { status: 200 })
        : new Response(CAPTCHA_BODY, { status: 400, headers: { 'Content-Type': 'application/json' } }));
}

const window = {
    TURNSTILE_SITE_KEY: '0xTEST',
    fetch: backend,
    turnstile: {
        render(_el, opts) {
            rendered = opts;
            setTimeout(() => opts.callback('tok'), 0);   // Turnstile solves itself
        },
        reset(_el) {
            setTimeout(() => rendered.callback('tok'), 0);
        },
    },
};
const document = { getElementById: (id) => (id === 'turnstile-container' ? container : null) };
const ctx = vm.createContext({
    window, document, console, setTimeout, clearTimeout, FormData, Response, Promise,
});
vm.runInContext(source, ctx);

const upload = () => {
    const fd = new FormData();
    fd.append('file', 'pretend-pdf');
    return window.fetch('/api/pdf-organize/compress/', { method: 'POST', body: fd });
};

// 1 + 2: rejected upload is solved and replayed; the caller only sees success.
const first = await upload();
assert.strictEqual(first.status, 200, 'the rejected upload was not replayed');
assert.deepStrictEqual(calls, [null, 'tok'], 'the replay must carry the token');
assert.ok(rendered, 'no widget was rendered');
assert.strictEqual(rendered.appearance, 'interaction-only', 'the challenge must solve without user interaction');

// 3: a 400 that is not a file upload is none of the interceptor's business.
calls.length = 0;
const plain = await window.fetch('/api/whatever/', { method: 'POST', body: '{"x":1}' });
assert.strictEqual(plain.status, 400, 'non-upload responses must pass through');
assert.deepStrictEqual(calls, [null], 'a non-upload must not be replayed');

// 4: the replay budget is finite (2 per page load; one is already spent).
calls.length = 0;
await upload();                       // spends the second
const exhausted = await upload();     // budget gone -> the 400 reaches the caller
assert.strictEqual(exhausted.status, 400, 'automatic replays must stop at the budget');

console.log('ok');
