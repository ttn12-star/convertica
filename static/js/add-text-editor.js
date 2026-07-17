// add-text-editor.js — Add Text page: the text/whiteout/highlight subset of
// the shared PDF editor core (pdf-editor-core.js).
document.addEventListener('DOMContentLoaded', () => {
    'use strict';
    if (typeof window.initPdfEditor !== 'function') return;
    window.initPdfEditor({
        toolset: { text: true, whiteout: true, highlight: true, symbols: true },
        apiUrl: window.API_URL,
    });
});
