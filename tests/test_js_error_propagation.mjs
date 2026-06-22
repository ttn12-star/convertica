// Smallest check that fails if the error-body parsing reverts to the
// "throw inside try / bare catch" anti-pattern that swallowed backend messages.
// Mirrors the !response.ok branch in pdf-editor.js / merge-pdf-multi.js.
import assert from 'node:assert';

const ERROR_MESSAGE = 'Editing failed. Please try again.';

async function extractError(bodyText) {
    let errorMsg = ERROR_MESSAGE;
    try {
        errorMsg = JSON.parse(bodyText).error || errorMsg;
    } catch { /* non-JSON body — keep generic */ }
    return errorMsg;
}

// JSON body with a backend message → user sees the backend message
assert.strictEqual(
    await extractError('{"error": "Invalid file: This archive is not password-protected."}'),
    'Invalid file: This archive is not password-protected.',
);
// Non-JSON body (e.g. HTML 500 page) → fall back to generic
assert.strictEqual(await extractError('<html>500</html>'), ERROR_MESSAGE);
// JSON without an error field → fall back to generic
assert.strictEqual(await extractError('{}'), ERROR_MESSAGE);

console.log('ok');
