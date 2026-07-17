/**
 * PDF Editor — /pdf-editor/ bootstrap
 *
 * Full-toolset consumer of the shared engine in pdf-editor-core.js
 * (window.initPdfEditor). Unlike the Add Text page (text/whiteout/
 * highlight/symbols only), this page enables every op-type the backend
 * accepts: text, whiteout, highlight, symbols, image, signature, shape, ink.
 */
document.addEventListener('DOMContentLoaded', () => {
    'use strict';
    if (typeof window.initPdfEditor !== 'function') return;
    window.initPdfEditor({
        toolset: {
            text: true, whiteout: true, highlight: true, symbols: true,
            image: true, signature: true, shape: true, ink: true,
        },
        apiUrl: window.API_URL,
    });
});
