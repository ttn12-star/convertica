/**
 * PDF Editor Core
 *
 * Shared engine behind Convertica's PDF annotation tools: pdf.js preview
 * render, an overlay document model, click-to-place, drag/resize handles,
 * page thumbnails/selector, undo/redo (immutable JSON snapshots, Ctrl+Z/Y),
 * zoom, a sessionStorage draft, and submit (POST `pdf_file` + `operations`
 * JSON, reusing the existing async/download flow).
 *
 * Extracted from add-text-editor.js (the first shipped consumer — the Add
 * Text tool) so a later, richer editor page can reuse the same engine
 * instead of forking it. Behavior for the add-text toolset
 * (text/whiteout/highlight/symbols) is unchanged by this extraction.
 *
 * Usage: window.initPdfEditor(opts) where
 *   opts = {
 *     toolset: { text, whiteout, highlight, symbols, image, signature, shape, ink },
 *     apiUrl,            // submit endpoint; defaults to window.API_URL
 *     i18n,              // optional string overrides; falls back to the
 *                        // same window.* globals the page already sets
 *     draftKeyPrefix,    // sessionStorage draft key prefix; defaults to
 *                        // 'convertica_addtext_' (the key add-text has
 *                        // always used — keep it stable so in-progress
 *                        // drafts survive this refactor)
 *   }
 *
 * The overlay model supports 8 op types, all toolset-gated and wired end to
 * end (create -> undo/redo -> submit serialization): text/whiteout/highlight
 * (click-to-place), image/signature (file-pick or draw/type/upload modal,
 * stamped centered on the page), and shape/ink (drag-to-draw on the canvas
 * with a live SVG preview):
 *   image/signature: {type,page,x,y,width,height,image_data_uri}
 *   shape:           {type,page,x,y,width,height,shape_kind,stroke,stroke_width,fill,fill_opacity}
 *   ink:             {type,page,x,y,width,height,points:[[x,y]...],stroke,stroke_width}
 * (points are absolute PDF-point page coordinates; the backend draws them
 * verbatim, independent of the op's x/y/width/height box.)
 *
 * DOM contract for the new tool UIs (all optional — a null lookup just
 * disables that control, matching the existing text-toolbar convention):
 *   Image:     #imageInsertBtn, #imageFileInput (hidden file input)
 *   Signature: #signatureInsertBtn, #signatureModal (+ #signatureModalClose/
 *              Apply/UseSaved), [data-sig-tab] + #sigTabDraw/Type/Upload,
 *              #signatureDrawCanvas/Clear, #signatureTypeText/Preview,
 *              #signatureUploadInput/Button/FileName (ported from
 *              sign-pdf-editor.js; localStorage key 'convertica_signature_v1'
 *              is shared with it on purpose).
 *   Shape:     data-edit-mode="shape" toolbar button, [data-shape-kind]
 *              (rect/ellipse/line/arrow), #shapeStrokeColorInput/WidthInput,
 *              #shapeFillEnabledCheckbox, #shapeFillColorInput/OpacityInput.
 *   Ink:       data-edit-mode="ink" toolbar button, #inkStrokeColorInput/
 *              WidthInput.
 *
 * Reuses window helpers: showLoading, hideLoading, showError,
 * showDownloadButton, CSRF_TOKEN, FILE_INPUT_NAME.
 */
(function () {
    'use strict';

    function initPdfEditor(opts) {
        opts = opts || {};
        const toolset = opts.toolset || {};
        const apiUrl = opts.apiUrl || window.API_URL;
        const i18n = opts.i18n || {};
        const draftPrefix = opts.draftKeyPrefix || 'convertica_addtext_';
        function t(key, fallback) {
            return i18n[key] || window[key] || fallback;
        }

        // ---------- PDF.js loader (mirrors sign-pdf-editor.js) -------------------
        const PDFJS_VERSION = '3.11.174';
        const localPdfSrc = typeof window.PDFJS_LOCAL_PDF === 'string' ? window.PDFJS_LOCAL_PDF : null;
        const localWorkerSrc = typeof window.PDFJS_LOCAL_WORKER === 'string' ? window.PDFJS_LOCAL_WORKER : null;
        const PDFJS_CANDIDATES = [
            ...(localPdfSrc ? [localPdfSrc] : []),
            `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}/pdf.min.js`,
            `https://unpkg.com/pdfjs-dist@${PDFJS_VERSION}/build/pdf.min.js`,
        ];
        const PDFJS_WORKER_CANDIDATES = [
            ...(localWorkerSrc ? [localWorkerSrc] : []),
            `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}/pdf.worker.min.js`,
            `https://unpkg.com/pdfjs-dist@${PDFJS_VERSION}/build/pdf.worker.min.js`,
        ];

        function loadExternalScript(src) {
            return new Promise((resolve, reject) => {
                const existing = Array.from(document.scripts).find((s) => s.src === src);
                if (existing) {
                    if (typeof window.pdfjsLib !== 'undefined') return resolve();
                    existing.addEventListener('load', () => resolve(), { once: true });
                    existing.addEventListener('error', () => reject(new Error('Failed to load ' + src)), { once: true });
                    return;
                }
                const script = document.createElement('script');
                script.src = src;
                script.async = true;
                script.crossOrigin = 'anonymous';
                script.onload = () => resolve();
                script.onerror = () => reject(new Error('Failed to load ' + src));
                document.head.appendChild(script);
            });
        }

        async function ensurePdfJsLoaded() {
            if (typeof window.pdfjsLib !== 'undefined') {
                if (!window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
                    window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CANDIDATES[0];
                }
                return true;
            }
            for (const src of PDFJS_CANDIDATES) {
                try {
                    await loadExternalScript(src);
                    if (typeof window.pdfjsLib !== 'undefined') break;
                } catch (_) { /* try next */ }
            }
            if (typeof window.pdfjsLib === 'undefined') return false;
            window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CANDIDATES[0];
            return true;
        }

        // ---------- DOM ----------------------------------------------------------
        const form = document.getElementById('editorForm');
        if (!form) return;
        const fileInput = document.getElementById('fileInput');
        const fileInputDrop = document.getElementById('fileInputDrop');
        const previewSection = document.getElementById('pdfPreviewSection');
        const pdfCanvas = document.getElementById('pdfCanvas');
        const pdfCanvasContainer = document.getElementById('pdfCanvasContainer');
        const pageSelector = document.getElementById('pageSelector');
        const submitButton = document.getElementById('editButton');
        const placementHint = document.getElementById('placementHint');

        // Toolbar
        const modeButtons = document.querySelectorAll('[data-edit-mode]');
        const symbolButtons = document.querySelectorAll('[data-symbol]');
        const fontSelect = document.getElementById('textFontSelect');
        const sizeInput = document.getElementById('textSizeInput');
        const colorInput = document.getElementById('textColorInput');
        const boldBtn = document.getElementById('textBoldBtn');
        const italicBtn = document.getElementById('textItalicBtn');
        const underlineBtn = document.getElementById('textUnderlineBtn');
        const alignButtons = document.querySelectorAll('[data-align]');
        const undoBtn = document.getElementById('undoBtn');
        const redoBtn = document.getElementById('redoBtn');
        const zoomInBtn = document.getElementById('zoomInBtn');
        const zoomOutBtn = document.getElementById('zoomOutBtn');
        const zoomLabel = document.getElementById('zoomLabel');

        // Image
        const imageInsertBtn = document.getElementById('imageInsertBtn');
        const imageFileInput = document.getElementById('imageFileInput');
        // Signature (modal, ported from sign-pdf-editor.js)
        const signatureInsertBtn = document.getElementById('signatureInsertBtn');
        const signatureModal = document.getElementById('signatureModal');
        const signatureModalClose = document.getElementById('signatureModalClose');
        const signatureModalApply = document.getElementById('signatureModalApply');
        const signatureModalUseSaved = document.getElementById('signatureModalUseSaved');
        const sigTabButtons = document.querySelectorAll('[data-sig-tab]');
        const sigTabPanels = {
            draw: document.getElementById('sigTabDraw'),
            type: document.getElementById('sigTabType'),
            upload: document.getElementById('sigTabUpload'),
        };
        const sigDrawCanvas = document.getElementById('signatureDrawCanvas');
        const sigDrawClearBtn = document.getElementById('signatureDrawClear');
        const sigTypeInput = document.getElementById('signatureTypeText');
        const sigTypePreviewCanvas = document.getElementById('signatureTypePreview');
        const sigUploadInput = document.getElementById('signatureUploadInput');
        const sigUploadButton = document.getElementById('signatureUploadButton');
        const sigUploadFileName = document.getElementById('signatureUploadFileName');
        // Shape
        const shapeKindButtons = document.querySelectorAll('[data-shape-kind]');
        const shapeStrokeColorInput = document.getElementById('shapeStrokeColorInput');
        const shapeStrokeWidthInput = document.getElementById('shapeStrokeWidthInput');
        const shapeFillEnabledCheckbox = document.getElementById('shapeFillEnabledCheckbox');
        const shapeFillColorInput = document.getElementById('shapeFillColorInput');
        const shapeFillOpacityInput = document.getElementById('shapeFillOpacityInput');
        // Ink
        const inkStrokeColorInput = document.getElementById('inkStrokeColorInput');
        const inkStrokeWidthInput = document.getElementById('inkStrokeWidthInput');

        const FONT_STACKS = {
            sans: "'Noto Sans', 'Segoe UI', Arial, sans-serif",
            serif: "'Noto Serif', Georgia, 'Times New Roman', serif",
            mono: "'Noto Sans Mono', 'Courier New', monospace",
        };
        const ARABIC_RE = /[؀-ۿݐ-ݿ]/;
        const HIGHLIGHT_DEFAULT = '#ffee00';
        const MAX_IMAGE_BYTES = 3 * 1024 * 1024; // matches backend cap (image/signature)
        const IMAGE_MIME_WHITELIST = ['image/png', 'image/jpeg', 'image/webp'];
        const SIGNATURE_STORAGE_KEY = 'convertica_signature_v1'; // shared w/ sign-pdf-editor.js
        const MAX_INK_POINTS = 2000; // matches backend cap
        const INK_MIN_POINT_DIST = 2; // screen px between recorded points (throttling)

        // ---------- State ---------------------------------------------------------
        let pdfDoc = null;
        let pageCount = 0;
        let currentPage = 1;       // 1-indexed for UI
        let fitScale = 1.0;        // canvas px per PDF point at zoom 1
        let zoomFactor = 1.0;
        let scale = 1.0;           // fitScale * zoomFactor
        let currentRenderTask = null;
        let mode = toolset.text ? 'text' : (toolset.whiteout ? 'whiteout' : (toolset.highlight ? 'highlight' : 'text'));
        let selectedId = null;
        let nextOpId = 1;
        let draftKey = null;
        /** ops: array of {id, type, page(1-idx), x, y, w, h (PDF points), ...
         *  type-specific fields, element (DOM overlay, current page only)}
         *  text:      text, fontKey, fontSize(pt), color, bold, italic, underline, align
         *  whiteout/highlight: color
         *  image/signature: imageDataUri
         *  shape:     shapeKind, stroke, strokeWidth, fill, fillOpacity
         *  ink:       points, stroke, strokeWidth
         */
        let ops = [];
        const undoStack = [];
        const redoStack = [];

        // ---------- History -------------------------------------------------------
        function serializeOps() {
            return ops.map(({ element, ...rest }) => ({ ...rest }));
        }
        function pushHistory() {
            undoStack.push(JSON.stringify(serializeOps()));
            if (undoStack.length > 100) undoStack.shift();
            redoStack.length = 0;
            updateHistoryButtons();
            saveDraftSoon();
        }
        function restoreSnapshot(json) {
            ops.forEach((o) => o.element && o.element.remove());
            ops = JSON.parse(json).map((o) => ({ ...o, element: null }));
            nextOpId = ops.reduce((m, o) => Math.max(m, o.id), 0) + 1;
            selectedId = null;
            rebuildOverlays();
            updateHistoryButtons();
            saveDraftSoon();
        }
        function undo() {
            if (!undoStack.length) return;
            redoStack.push(JSON.stringify(serializeOps()));
            restoreSnapshot(undoStack.pop());
        }
        function redo() {
            if (!redoStack.length) return;
            undoStack.push(JSON.stringify(serializeOps()));
            restoreSnapshot(redoStack.pop());
        }
        function updateHistoryButtons() {
            if (undoBtn) undoBtn.disabled = undoStack.length === 0;
            if (redoBtn) redoBtn.disabled = redoStack.length === 0;
        }
        if (undoBtn) undoBtn.addEventListener('click', undo);
        if (redoBtn) redoBtn.addEventListener('click', redo);
        updateHistoryButtons();

        // ---------- Draft persistence (survive reloads) ---------------------------
        let draftTimer = null;
        function saveDraftSoon() {
            if (!draftKey) return;
            clearTimeout(draftTimer);
            draftTimer = setTimeout(() => {
                try {
                    sessionStorage.setItem(draftKey, JSON.stringify(serializeOps()));
                } catch (_) { /* quota; ignore */ }
            }, 400);
        }
        function tryRestoreDraft() {
            if (!draftKey) return false;
            let raw = null;
            try { raw = sessionStorage.getItem(draftKey); } catch (_) { /* ignore */ }
            if (!raw) return false;
            try {
                const parsed = JSON.parse(raw);
                if (!Array.isArray(parsed) || !parsed.length) return false;
                ops = parsed.map((o) => ({ ...o, element: null }));
                nextOpId = ops.reduce((m, o) => Math.max(m, o.id), 0) + 1;
                return true;
            } catch (_) { return false; }
        }

        // ---------- Mode switching -------------------------------------------------
        // Contextual property panels: show only the active tool's controls so
        // the toolbar isn't a wall of every tool's settings at once. A mode with
        // no panel (whiteout/highlight) simply shows none — the placement hint
        // covers it. No-ops on the add-text page, which ships no [data-tool-panel].
        const toolPanels = document.querySelectorAll('[data-tool-panel]');
        function setMode(newMode) {
            if (!toolset[newMode]) return; // guard: never switch into a disabled tool
            mode = newMode;
            modeButtons.forEach((btn) => {
                const active = btn.dataset.editMode === newMode;
                btn.classList.toggle('bg-blue-600', active);
                btn.classList.toggle('text-white', active);
                btn.classList.toggle('bg-gray-100', !active);
                btn.classList.toggle('dark:bg-gray-700', !active);
                btn.classList.toggle('text-gray-700', !active);
                btn.classList.toggle('dark:text-gray-200', !active);
            });
            toolPanels.forEach((panel) => {
                panel.style.display = panel.dataset.toolPanel === newMode ? '' : 'none';
            });
            if (pdfCanvas) pdfCanvas.style.cursor = 'crosshair';
        }
        modeButtons.forEach((btn) => {
            const btnMode = btn.dataset.editMode;
            if (!toolset[btnMode]) {
                btn.style.display = 'none';
                return;
            }
            btn.addEventListener('click', () => setMode(btnMode));
        });
        setMode(mode);

        // ---------- Selection + toolbar sync ---------------------------------------
        function selectedOp() {
            return ops.find((o) => o.id === selectedId) || null;
        }
        function setSelected(id) {
            selectedId = id;
            ops.forEach((o) => {
                if (o.element) {
                    o.element.classList.toggle('ate-selected', o.id === id);
                }
            });
            syncToolbarFromSelection();
        }
        function syncToolbarFromSelection() {
            const op = selectedOp();
            if (!op || op.type !== 'text') return;
            if (fontSelect) fontSelect.value = op.fontKey;
            if (sizeInput) sizeInput.value = String(op.fontSize);
            if (colorInput) colorInput.value = op.color;
            if (boldBtn) boldBtn.classList.toggle('ate-toggle-on', !!op.bold);
            if (italicBtn) italicBtn.classList.toggle('ate-toggle-on', !!op.italic);
            if (underlineBtn) underlineBtn.classList.toggle('ate-toggle-on', !!op.underline);
            alignButtons.forEach((b) => b.classList.toggle('ate-toggle-on', b.dataset.align === op.align));
        }
        function applyStyleChange(mutator) {
            const op = selectedOp();
            pushHistory();
            // With a selection: restyle it. Without: the change only sets defaults
            // for the next box (defaults read from the toolbar at creation time).
            if (op && op.type === 'text') {
                mutator(op);
                styleOverlay(op);
                saveDraftSoon();
            }
        }
        if (toolset.text) {
            if (fontSelect) fontSelect.addEventListener('change', () => applyStyleChange((o) => { o.fontKey = fontSelect.value; }));
            if (sizeInput) sizeInput.addEventListener('change', () => {
                const v = Math.max(6, Math.min(96, parseFloat(sizeInput.value) || 14));
                sizeInput.value = String(v);
                applyStyleChange((o) => { o.fontSize = v; });
            });
            if (colorInput) colorInput.addEventListener('input', () => applyStyleChange((o) => { o.color = colorInput.value; }));
        }
        function toggleFlag(btn, key) {
            if (!btn) return;
            btn.addEventListener('click', () => {
                const op = selectedOp();
                const nowOn = !(op && op.type === 'text' ? op[key] : btn.classList.contains('ate-toggle-on'));
                btn.classList.toggle('ate-toggle-on', nowOn);
                applyStyleChange((o) => { o[key] = nowOn; });
            });
        }
        if (toolset.text) {
            toggleFlag(boldBtn, 'bold');
            toggleFlag(italicBtn, 'italic');
            toggleFlag(underlineBtn, 'underline');
            alignButtons.forEach((btn) => {
                btn.addEventListener('click', () => {
                    alignButtons.forEach((b) => b.classList.toggle('ate-toggle-on', b === btn));
                    applyStyleChange((o) => { o.align = btn.dataset.align; });
                });
            });
        }

        function toolbarDefaults() {
            const alignBtn = Array.from(alignButtons).find((b) => b.classList.contains('ate-toggle-on'));
            return {
                fontKey: fontSelect ? fontSelect.value : 'sans',
                fontSize: sizeInput ? Math.max(6, Math.min(96, parseFloat(sizeInput.value) || 14)) : 14,
                color: colorInput ? colorInput.value : '#111111',
                bold: !!(boldBtn && boldBtn.classList.contains('ate-toggle-on')),
                italic: !!(italicBtn && italicBtn.classList.contains('ate-toggle-on')),
                underline: !!(underlineBtn && underlineBtn.classList.contains('ate-toggle-on')),
                align: alignBtn ? alignBtn.dataset.align : 'left',
            };
        }

        // ---------- PDF load + render ----------------------------------------------
        async function handleFileSelected(file) {
            if (!file) return;
            const ok = await ensurePdfJsLoaded();
            if (!ok) {
                window.showError && window.showError(
                    t('FAILED_TO_LOAD_PDF', 'Failed to load PDF preview.'), 'editorResult'
                );
                return;
            }
            cleanupPreviousPDF();
            try {
                const arrayBuf = await file.arrayBuffer();
                pdfDoc = await window.pdfjsLib.getDocument({
                    data: arrayBuf, disableAutoFetch: true, disableStream: true,
                }).promise;
            } catch (e) {
                window.showError && window.showError(
                    t('FAILED_TO_LOAD_PDF', 'Failed to load PDF preview.'), 'editorResult'
                );
                return;
            }
            pageCount = pdfDoc.numPages;
            currentPage = 1;
            draftKey = draftPrefix + file.name + '_' + file.size;
            tryRestoreDraft();
            populatePageSelector();
            await renderPage(currentPage);
            rebuildOverlays();
            previewSection && previewSection.classList.remove('hidden');
            placementHint && placementHint.classList.remove('hidden');
            submitButton && (submitButton.disabled = false);
        }

        function cleanupPreviousPDF() {
            if (pdfDoc) {
                try { pdfDoc.destroy(); } catch (_) { /* ignore */ }
                pdfDoc = null;
            }
            pageCount = 0;
            currentPage = 1;
            zoomFactor = 1.0;
            ops.forEach((o) => o.element && o.element.remove());
            ops = [];
            undoStack.length = 0;
            redoStack.length = 0;
            selectedId = null;
            updateHistoryButtons();
            if (pdfCanvas) {
                const ctx = pdfCanvas.getContext('2d');
                ctx && ctx.clearRect(0, 0, pdfCanvas.width, pdfCanvas.height);
            }
        }

        function populatePageSelector() {
            if (!pageSelector) return;
            pageSelector.innerHTML = '';
            for (let i = 1; i <= pageCount; i++) {
                const opt = document.createElement('option');
                opt.value = String(i);
                opt.textContent = t('PAGE_LABEL', 'Page') + ' ' + i + ' / ' + pageCount;
                pageSelector.appendChild(opt);
            }
            pageSelector.value = '1';
        }
        if (pageSelector) {
            pageSelector.addEventListener('change', async () => {
                const p = parseInt(pageSelector.value, 10);
                if (!isNaN(p) && p >= 1 && p <= pageCount) {
                    currentPage = p;
                    await renderPage(currentPage);
                    rebuildOverlays();
                }
            });
        }

        async function renderPage(pageNum) {
            if (!pdfDoc) return;
            const page = await pdfDoc.getPage(pageNum);
            const baseViewport = page.getViewport({ scale: 1.0 });

            const maxWidth = 640;
            const maxHeight = 760;
            fitScale = Math.min(maxWidth / baseViewport.width, maxHeight / baseViewport.height, 1.25);
            scale = fitScale * zoomFactor;
            const scaledViewport = page.getViewport({ scale });

            pdfCanvas.width = scaledViewport.width;
            pdfCanvas.height = scaledViewport.height;
            pdfCanvas.style.width = '';
            pdfCanvas.style.height = '';

            if (currentRenderTask) {
                try { currentRenderTask.cancel(); } catch (_) { /* ignore */ }
                currentRenderTask = null;
            }
            currentRenderTask = page.render({
                canvasContext: pdfCanvas.getContext('2d'),
                viewport: scaledViewport,
            });
            try { await currentRenderTask.promise; } catch (_) { /* render cancelled */ }
            currentRenderTask = null;
            if (zoomLabel) zoomLabel.textContent = Math.round(zoomFactor * 100) + '%';
        }

        async function setZoom(factor) {
            zoomFactor = Math.max(0.5, Math.min(2.0, factor));
            await renderPage(currentPage);
            rebuildOverlays();
        }
        if (zoomInBtn) zoomInBtn.addEventListener('click', () => setZoom(zoomFactor + 0.25));
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => setZoom(zoomFactor - 0.25));

        // ---------- Object creation -------------------------------------------------
        function sampleCanvasColor(px, py) {
            try {
                const d = pdfCanvas.getContext('2d').getImageData(Math.round(px), Math.round(py), 1, 1).data;
                const hex = (n) => n.toString(16).padStart(2, '0');
                return '#' + hex(d[0]) + hex(d[1]) + hex(d[2]);
            } catch (_) {
                return '#ffffff';
            }
        }

        if (pdfCanvas) {
            pdfCanvas.addEventListener('click', (ev) => {
                if (!pdfDoc) return;
                // Shape/ink are drag-to-draw (separate pointerdown/move/up handlers
                // below); a plain click while in one of those modes places nothing.
                if (mode === 'shape' || mode === 'ink') return;
                const rect = pdfCanvas.getBoundingClientRect();
                const px = ev.clientX - rect.left;
                const py = ev.clientY - rect.top;
                const x = px / scale;
                const y = py / scale;

                let op;
                if (mode === 'whiteout' && toolset.whiteout) {
                    op = {
                        id: nextOpId++, type: 'whiteout', page: currentPage,
                        x: x - 60, y: y - 12, w: 120, h: 24,
                        color: sampleCanvasColor(px, py),
                    };
                } else if (mode === 'highlight' && toolset.highlight) {
                    op = {
                        id: nextOpId++, type: 'highlight', page: currentPage,
                        x: x - 80, y: y - 10, w: 160, h: 20,
                        color: HIGHLIGHT_DEFAULT,
                    };
                } else if (mode === 'text' && toolset.text) {
                    const d = toolbarDefaults();
                    op = {
                        id: nextOpId++, type: 'text', page: currentPage,
                        x: x - 10, y: y - d.fontSize * 0.8, w: 220, h: Math.max(28, d.fontSize * 2),
                        text: '', ...d,
                    };
                } else {
                    return;
                }
                // pushHistory() only after we know an op will actually be created —
                // a click that matches no active tool must not push a spurious
                // empty undo snapshot (papercut from the Task 4 extraction).
                pushHistory();
                op.x = Math.max(0, op.x);
                op.y = Math.max(0, op.y);
                ops.push(op);
                buildOverlayElement(op);
                setSelected(op.id);
                if (op.type === 'text') focusTextEditing(op);
                saveDraftSoon();
            });
        }

        function insertSymbol(symbol) {
            if (!pdfDoc || !toolset.text) return;
            pushHistory();
            const d = toolbarDefaults();
            const size = Math.max(d.fontSize, 18);
            const op = {
                id: nextOpId++, type: 'text', page: currentPage,
                x: 40 / scale, y: 40 / scale, w: size * 2, h: size * 1.8,
                text: symbol, ...d, fontSize: size,
            };
            ops.push(op);
            buildOverlayElement(op);
            setSelected(op.id);
            saveDraftSoon();
        }
        symbolButtons.forEach((btn) => {
            if (!toolset.symbols) {
                btn.style.display = 'none';
                return;
            }
            btn.addEventListener('click', () => insertSymbol(btn.dataset.symbol));
        });

        // ---------- Shared stamp-style insertion (image/signature) ------------------
        // Both tools produce a PNG/JPEG/WEBP data-URI and drop it onto the current
        // page centered, sized from its natural aspect ratio — same "insert then
        // drag/resize into place" UX as insertSymbol() above, reusing the identical
        // model -> history -> overlay pipeline.
        function clampNum(v, lo, hi) {
            return Math.max(lo, Math.min(hi, v));
        }

        function readFileAsDataUri(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(String(reader.result || ''));
                reader.onerror = () => reject(reader.error || new Error('read failed'));
                reader.readAsDataURL(file);
            });
        }

        function dataUriDecodedByteLength(dataUri) {
            const idx = dataUri.indexOf(',');
            const b64 = idx >= 0 ? dataUri.slice(idx + 1) : dataUri;
            const padding = b64.endsWith('==') ? 2 : b64.endsWith('=') ? 1 : 0;
            return Math.floor((b64.length * 3) / 4) - padding;
        }

        function loadImageNaturalSize(dataUri) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => resolve({
                    width: img.naturalWidth || img.width || 200,
                    height: img.naturalHeight || img.height || 120,
                });
                img.onerror = () => reject(new Error('decode failed'));
                img.src = dataUri;
            });
        }

        async function insertStampOp(type, dataUri) {
            if (!pdfDoc) return;
            const dims = await loadImageNaturalSize(dataUri).catch(() => ({ width: 200, height: 120 }));
            const pageW = pdfCanvas.width / scale;
            const pageH = pdfCanvas.height / scale;
            const aspect = dims.height / dims.width || 0.6;
            // Floor at 4pt to match the server serializer's min_value=4
            // (extreme-aspect images could otherwise round below it).
            const w = Math.max(4, Math.min(240, pageW * 0.6));
            const h = Math.max(4, w * aspect);
            pushHistory();
            const op = {
                id: nextOpId++, type, page: currentPage,
                x: Math.max(0, (pageW - w) / 2), y: Math.max(0, (pageH - h) / 2),
                w, h, imageDataUri: dataUri,
            };
            ops.push(op);
            buildOverlayElement(op);
            setSelected(op.id);
            saveDraftSoon();
        }

        // ---------- Image tool --------------------------------------------------------
        if (toolset.image) {
            if (imageInsertBtn) {
                imageInsertBtn.addEventListener('click', () => {
                    if (!pdfDoc || !imageFileInput) return;
                    imageFileInput.click();
                });
            }
            if (imageFileInput) {
                imageFileInput.addEventListener('change', async () => {
                    const file = imageFileInput.files && imageFileInput.files[0];
                    imageFileInput.value = ''; // allow re-picking the same file
                    if (!file || !pdfDoc) return;
                    if (IMAGE_MIME_WHITELIST.indexOf(file.type) === -1) {
                        window.showError && window.showError(
                            t('IMAGE_TYPE_MESSAGE', 'Please choose a PNG, JPEG, or WEBP image.'), 'editorResult'
                        );
                        return;
                    }
                    let dataUri;
                    try {
                        dataUri = await readFileAsDataUri(file);
                    } catch (_) {
                        window.showError && window.showError(
                            t('FAILED_TO_LOAD_IMAGE_MESSAGE', 'Failed to read the image.'), 'editorResult'
                        );
                        return;
                    }
                    if (dataUriDecodedByteLength(dataUri) > MAX_IMAGE_BYTES) {
                        window.showError && window.showError(
                            t('IMAGE_TOO_LARGE_MESSAGE', 'Image is too large (max 3MB).'), 'editorResult'
                        );
                        return;
                    }
                    insertStampOp('image', dataUri);
                });
            }
        } else if (imageInsertBtn) {
            imageInsertBtn.style.display = 'none';
        }

        // ---------- Signature tool (modal ported from sign-pdf-editor.js) -----------
        if (toolset.signature && signatureModal) {
            (function initSignatureModule() {
                let sigUploadedDataUri = null;

                function setActiveSigTab(name) {
                    sigTabButtons.forEach((btn) => {
                        const active = btn.dataset.sigTab === name;
                        btn.classList.toggle('border-blue-600', active);
                        btn.classList.toggle('text-blue-600', active);
                        btn.classList.toggle('border-transparent', !active);
                        btn.classList.toggle('text-gray-500', !active);
                    });
                    Object.entries(sigTabPanels).forEach(([n, panel]) => {
                        if (panel) panel.classList.toggle('hidden', n !== name);
                    });
                }
                sigTabButtons.forEach((btn) => {
                    btn.addEventListener('click', () => setActiveSigTab(btn.dataset.sigTab));
                });

                function activeSigTab() {
                    for (const btn of sigTabButtons) {
                        if (btn.classList.contains('text-blue-600')) return btn.dataset.sigTab;
                    }
                    return 'draw';
                }

                // Draw tab: capture pointer strokes on a small transparent canvas.
                if (sigDrawCanvas) {
                    const ctx = sigDrawCanvas.getContext('2d');
                    let drawing = false;
                    let lastX = 0, lastY = 0;
                    function paintBackground() {
                        ctx.clearRect(0, 0, sigDrawCanvas.width, sigDrawCanvas.height);
                    }
                    paintBackground();
                    function pointFromEvent(ev) {
                        const rect = sigDrawCanvas.getBoundingClientRect();
                        return {
                            x: (ev.clientX - rect.left) * (sigDrawCanvas.width / rect.width),
                            y: (ev.clientY - rect.top) * (sigDrawCanvas.height / rect.height),
                        };
                    }
                    sigDrawCanvas.addEventListener('pointerdown', (ev) => {
                        ev.preventDefault();
                        drawing = true;
                        const p = pointFromEvent(ev);
                        lastX = p.x; lastY = p.y;
                    });
                    sigDrawCanvas.addEventListener('pointermove', (ev) => {
                        if (!drawing) return;
                        ev.preventDefault();
                        const p = pointFromEvent(ev);
                        ctx.strokeStyle = '#111827';
                        ctx.lineWidth = 2.5;
                        ctx.lineCap = 'round';
                        ctx.lineJoin = 'round';
                        ctx.beginPath();
                        ctx.moveTo(lastX, lastY);
                        ctx.lineTo(p.x, p.y);
                        ctx.stroke();
                        lastX = p.x; lastY = p.y;
                    });
                    ['pointerup', 'pointerleave', 'pointercancel'].forEach((evt) => {
                        sigDrawCanvas.addEventListener(evt, (ev) => { ev.preventDefault(); drawing = false; });
                    });
                    if (sigDrawClearBtn) sigDrawClearBtn.addEventListener('click', paintBackground);
                }

                // Type tab: render a typed name in a handwriting font.
                function renderTypedSignature() {
                    if (!sigTypeInput || !sigTypePreviewCanvas) return;
                    const text = (sigTypeInput.value || '').trim();
                    const ctx = sigTypePreviewCanvas.getContext('2d');
                    ctx.clearRect(0, 0, sigTypePreviewCanvas.width, sigTypePreviewCanvas.height);
                    if (!text) return;
                    let fontSize = 64;
                    ctx.fillStyle = '#111827';
                    do {
                        ctx.font = `${fontSize}px "Caveat", "Brush Script MT", cursive`;
                        if (ctx.measureText(text).width <= sigTypePreviewCanvas.width - 30) break;
                        fontSize -= 2;
                    } while (fontSize > 20);
                    ctx.textBaseline = 'middle';
                    ctx.fillText(text, 15, sigTypePreviewCanvas.height / 2);
                }
                if (sigTypeInput) sigTypeInput.addEventListener('input', renderTypedSignature);

                // Upload tab: file -> data URI (same MIME/size gate as the image tool).
                if (sigUploadButton && sigUploadInput) {
                    sigUploadButton.addEventListener('click', () => sigUploadInput.click());
                }
                if (sigUploadInput) {
                    sigUploadInput.addEventListener('change', async () => {
                        const file = sigUploadInput.files && sigUploadInput.files[0];
                        if (!file) return;
                        if (IMAGE_MIME_WHITELIST.indexOf(file.type) === -1) {
                            window.showError && window.showError(
                                t('IMAGE_TYPE_MESSAGE', 'Please choose a PNG, JPEG, or WEBP image.'), 'editorResult'
                            );
                            return;
                        }
                        let dataUri;
                        try {
                            dataUri = await readFileAsDataUri(file);
                        } catch (_) { return; }
                        if (dataUriDecodedByteLength(dataUri) > MAX_IMAGE_BYTES) {
                            window.showError && window.showError(
                                t('IMAGE_TOO_LARGE_MESSAGE', 'Image is too large (max 3MB).'), 'editorResult'
                            );
                            return;
                        }
                        sigUploadedDataUri = dataUri;
                        if (sigUploadFileName) sigUploadFileName.textContent = file.name;
                    });
                }

                function buildSignatureDataUri() {
                    const tab = activeSigTab();
                    if (tab === 'draw' && sigDrawCanvas) return sigDrawCanvas.toDataURL('image/png');
                    if (tab === 'type' && sigTypePreviewCanvas) {
                        renderTypedSignature();
                        return sigTypePreviewCanvas.toDataURL('image/png');
                    }
                    if (tab === 'upload') return sigUploadedDataUri;
                    return null;
                }

                function updateUseSavedVisibility() {
                    if (!signatureModalUseSaved) return;
                    let saved = null;
                    try { saved = localStorage.getItem(SIGNATURE_STORAGE_KEY); } catch (_) { /* ignore */ }
                    signatureModalUseSaved.classList.toggle('hidden', !saved);
                }
                updateUseSavedVisibility();

                function openModal() {
                    if (!pdfDoc) return;
                    signatureModal.classList.remove('hidden');
                    setActiveSigTab('draw');
                }
                function closeModal() {
                    signatureModal.classList.add('hidden');
                }
                if (signatureInsertBtn) signatureInsertBtn.addEventListener('click', openModal);
                if (signatureModalClose) signatureModalClose.addEventListener('click', closeModal);
                if (signatureModalApply) {
                    signatureModalApply.addEventListener('click', () => {
                        const dataUri = buildSignatureDataUri();
                        if (!dataUri || dataUri.length < 100) {
                            window.showError && window.showError(
                                t('SIGNATURE_EMPTY_MESSAGE', 'Please draw, type, or upload a signature first.'), 'editorResult'
                            );
                            return;
                        }
                        try { localStorage.setItem(SIGNATURE_STORAGE_KEY, dataUri); } catch (_) { /* quota; ignore */ }
                        updateUseSavedVisibility();
                        closeModal();
                        insertStampOp('signature', dataUri);
                    });
                }
                if (signatureModalUseSaved) {
                    signatureModalUseSaved.addEventListener('click', () => {
                        let saved = null;
                        try { saved = localStorage.getItem(SIGNATURE_STORAGE_KEY); } catch (_) { /* ignore */ }
                        if (!saved) return;
                        closeModal();
                        insertStampOp('signature', saved);
                    });
                }
            })();
        } else if (signatureInsertBtn) {
            signatureInsertBtn.style.display = 'none';
        }

        // ---------- Shape SVG rendering (shared by the live preview + real overlay) --
        const SVG_NS = 'http://www.w3.org/2000/svg';
        function buildShapeSvg(kind, w, h, stroke, strokeWidth, fill, fillOpacity) {
            w = Math.max(1, w); h = Math.max(1, h);
            const svg = document.createElementNS(SVG_NS, 'svg');
            svg.setAttribute('width', '100%');
            svg.setAttribute('height', '100%');
            svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
            svg.setAttribute('preserveAspectRatio', 'none');
            svg.style.display = 'block';
            svg.style.overflow = 'visible';
            svg.style.pointerEvents = 'none';
            const half = strokeWidth / 2;
            const fillAttr = fill || 'none';
            let shapeEl;
            if (kind === 'ellipse') {
                shapeEl = document.createElementNS(SVG_NS, 'ellipse');
                shapeEl.setAttribute('cx', w / 2);
                shapeEl.setAttribute('cy', h / 2);
                shapeEl.setAttribute('rx', Math.max(0, w / 2 - half));
                shapeEl.setAttribute('ry', Math.max(0, h / 2 - half));
            } else if (kind === 'line' || kind === 'arrow') {
                shapeEl = document.createElementNS(SVG_NS, 'line');
                shapeEl.setAttribute('x1', half); shapeEl.setAttribute('y1', half);
                shapeEl.setAttribute('x2', w - half); shapeEl.setAttribute('y2', h - half);
            } else {
                shapeEl = document.createElementNS(SVG_NS, 'rect');
                shapeEl.setAttribute('x', half); shapeEl.setAttribute('y', half);
                shapeEl.setAttribute('width', Math.max(0, w - strokeWidth));
                shapeEl.setAttribute('height', Math.max(0, h - strokeWidth));
            }
            shapeEl.setAttribute('stroke', stroke);
            shapeEl.setAttribute('stroke-width', strokeWidth);
            shapeEl.setAttribute('fill', kind === 'line' || kind === 'arrow' ? 'none' : fillAttr);
            if (fill && kind !== 'line' && kind !== 'arrow') shapeEl.setAttribute('fill-opacity', fillOpacity);
            svg.appendChild(shapeEl);
            if (kind === 'arrow') {
                const angle = Math.atan2(h - 2 * half, w - 2 * half);
                const headLen = Math.max(6, strokeWidth * 3);
                const tipX = w - half, tipY = h - half;
                const a1 = angle + (5 * Math.PI) / 6;
                const a2 = angle - (5 * Math.PI) / 6;
                const head = document.createElementNS(SVG_NS, 'polygon');
                head.setAttribute('points', [
                    `${tipX},${tipY}`,
                    `${tipX + headLen * Math.cos(a1)},${tipY + headLen * Math.sin(a1)}`,
                    `${tipX + headLen * Math.cos(a2)},${tipY + headLen * Math.sin(a2)}`,
                ].join(' '));
                head.setAttribute('fill', stroke);
                svg.appendChild(head);
            }
            return svg;
        }

        function buildInkSvg(op) {
            const w = Math.max(1, op.w), h = Math.max(1, op.h);
            const svg = document.createElementNS(SVG_NS, 'svg');
            svg.setAttribute('width', '100%');
            svg.setAttribute('height', '100%');
            svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
            svg.setAttribute('preserveAspectRatio', 'none');
            svg.style.display = 'block';
            svg.style.overflow = 'visible';
            svg.style.pointerEvents = 'none';
            const pts = (op.points || []).map(([px, py]) => `${px - op.x},${py - op.y}`).join(' ');
            const path = document.createElementNS(SVG_NS, 'polyline');
            path.setAttribute('points', pts);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', op.stroke || '#111111');
            path.setAttribute('stroke-width', op.strokeWidth || 2);
            path.setAttribute('stroke-linecap', 'round');
            path.setAttribute('stroke-linejoin', 'round');
            svg.appendChild(path);
            return svg;
        }

        // ---------- Shape tool (drag-to-draw) ----------------------------------------
        let currentShapeKind = 'rect';
        function shapeToolbarDefaults() {
            return {
                kind: currentShapeKind,
                stroke: shapeStrokeColorInput ? shapeStrokeColorInput.value : '#111111',
                strokeWidth: shapeStrokeWidthInput
                    ? clampNum(parseFloat(shapeStrokeWidthInput.value) || 2, 0.5, 20) : 2,
                fill: (shapeFillEnabledCheckbox && shapeFillEnabledCheckbox.checked && shapeFillColorInput)
                    ? shapeFillColorInput.value : null,
                fillOpacity: shapeFillOpacityInput
                    ? clampNum(parseFloat(shapeFillOpacityInput.value), 0, 1) : 1,
            };
        }
        function applyShapeStyleChange(mutator) {
            const op = selectedOp();
            if (op && op.type === 'shape') {
                pushHistory();
                mutator(op);
                styleOverlay(op);
                saveDraftSoon();
            }
        }
        if (toolset.shape) {
            shapeKindButtons.forEach((btn) => {
                btn.addEventListener('click', () => {
                    currentShapeKind = btn.dataset.shapeKind;
                    shapeKindButtons.forEach((b) => b.classList.toggle('ate-toggle-on', b === btn));
                    applyShapeStyleChange((o) => { o.shapeKind = currentShapeKind; });
                });
            });
            if (shapeStrokeColorInput) {
                shapeStrokeColorInput.addEventListener('input', () => applyShapeStyleChange((o) => { o.stroke = shapeStrokeColorInput.value; }));
            }
            if (shapeStrokeWidthInput) {
                shapeStrokeWidthInput.addEventListener('change', () => {
                    const v = clampNum(parseFloat(shapeStrokeWidthInput.value) || 2, 0.5, 20);
                    shapeStrokeWidthInput.value = String(v);
                    applyShapeStyleChange((o) => { o.strokeWidth = v; });
                });
            }
            if (shapeFillColorInput) {
                shapeFillColorInput.addEventListener('input', () => applyShapeStyleChange((o) => {
                    if (o.fill) o.fill = shapeFillColorInput.value;
                }));
            }
            if (shapeFillEnabledCheckbox) {
                shapeFillEnabledCheckbox.addEventListener('change', () => applyShapeStyleChange((o) => {
                    o.fill = shapeFillEnabledCheckbox.checked ? (shapeFillColorInput ? shapeFillColorInput.value : '#ffffff') : null;
                }));
            }
            if (shapeFillOpacityInput) {
                shapeFillOpacityInput.addEventListener('input', () => applyShapeStyleChange((o) => {
                    o.fillOpacity = clampNum(parseFloat(shapeFillOpacityInput.value), 0, 1);
                }));
            }

            let shapeDraft = null; // { startPx, startPy, previewEl, def }
            function boxFromDrag(x0, y0, x1, y1) {
                return {
                    xPx: Math.min(x0, x1), yPx: Math.min(y0, y1),
                    wPx: Math.abs(x1 - x0), hPx: Math.abs(y1 - y0),
                };
            }
            function positionPreview(el, box) {
                el.style.left = box.xPx + 'px';
                el.style.top = box.yPx + 'px';
                el.style.width = Math.max(1, box.wPx) + 'px';
                el.style.height = Math.max(1, box.hPx) + 'px';
            }
            function onShapeMove(ev) {
                if (!shapeDraft) return;
                ev.preventDefault();
                const rect = pdfCanvas.getBoundingClientRect();
                const box = boxFromDrag(shapeDraft.startPx, shapeDraft.startPy, ev.clientX - rect.left, ev.clientY - rect.top);
                positionPreview(shapeDraft.previewEl, box);
                const old = shapeDraft.previewEl.querySelector('svg');
                if (old) old.remove();
                shapeDraft.previewEl.appendChild(buildShapeSvg(
                    shapeDraft.def.kind, box.wPx, box.hPx,
                    shapeDraft.def.stroke, shapeDraft.def.strokeWidth * scale,
                    shapeDraft.def.fill, shapeDraft.def.fillOpacity
                ));
                shapeDraft.lastBox = box;
            }
            function onShapeUp() {
                if (!shapeDraft) return;
                window.removeEventListener('pointermove', onShapeMove);
                window.removeEventListener('pointerup', onShapeUp);
                const box = shapeDraft.lastBox || { xPx: shapeDraft.startPx, yPx: shapeDraft.startPy, wPx: 0, hPx: 0 };
                const def = shapeDraft.def;
                shapeDraft.previewEl.remove();
                shapeDraft = null;
                if (box.wPx < 4 && box.hPx < 4) return; // accidental click/tap: discard, no history push
                pushHistory();
                const op = {
                    id: nextOpId++, type: 'shape', page: currentPage,
                    x: box.xPx / scale, y: box.yPx / scale,
                    // Floor at 4pt to match the server serializer's min_value=4;
                    // a straight horizontal/vertical line/arrow has ~0 on one axis
                    // and would otherwise 400 the whole save.
                    w: Math.max(4, box.wPx / scale), h: Math.max(4, box.hPx / scale),
                    shapeKind: def.kind, stroke: def.stroke, strokeWidth: def.strokeWidth,
                    fill: def.fill, fillOpacity: def.fillOpacity,
                };
                ops.push(op);
                buildOverlayElement(op);
                setSelected(op.id);
                saveDraftSoon();
            }
            if (pdfCanvas) {
                pdfCanvas.addEventListener('pointerdown', (ev) => {
                    if (mode !== 'shape' || !pdfDoc || ev.target !== pdfCanvas) return;
                    ev.preventDefault();
                    const rect = pdfCanvas.getBoundingClientRect();
                    const startPx = ev.clientX - rect.left, startPy = ev.clientY - rect.top;
                    const previewEl = document.createElement('div');
                    previewEl.style.position = 'absolute';
                    previewEl.style.pointerEvents = 'none';
                    pdfCanvasContainer.appendChild(previewEl);
                    shapeDraft = { startPx, startPy, previewEl, def: shapeToolbarDefaults(), lastBox: null };
                    positionPreview(previewEl, { xPx: startPx, yPx: startPy, wPx: 0, hPx: 0 });
                    window.addEventListener('pointermove', onShapeMove);
                    window.addEventListener('pointerup', onShapeUp);
                });
            }
        }

        // ---------- Ink (freehand) tool (drag-to-draw) -------------------------------
        function inkToolbarDefaults() {
            return {
                stroke: inkStrokeColorInput ? inkStrokeColorInput.value : '#111111',
                strokeWidth: inkStrokeWidthInput
                    ? clampNum(parseFloat(inkStrokeWidthInput.value) || 2, 0.5, 20) : 2,
            };
        }
        // Keeps a dragged/resized ink stroke's absolute points in sync with the
        // overlay box that attachDragAndResize moves — otherwise the on-screen
        // preview would move but the materialized PDF (which draws `points`
        // verbatim, ignoring x/y/width/height) would not.
        function inkGeomHook(phase, op, start) {
            if (phase === 'begin') {
                op._dragOrigPoints = (op.points || []).map((p) => p.slice());
                return;
            }
            if (phase === 'end') {
                delete op._dragOrigPoints;
                return;
            }
            const orig = op._dragOrigPoints;
            if (!orig) return;
            if (phase === 'drag') {
                const dx = op.x - start.startX, dy = op.y - start.startY;
                op.points = orig.map(([px, py]) => [px + dx, py + dy]);
            } else if (phase === 'resize') {
                const sx = start.startW ? op.w / start.startW : 1;
                const sy = start.startH ? op.h / start.startH : 1;
                op.points = orig.map(([px, py]) => [
                    start.startX + (px - start.startX) * sx,
                    start.startY + (py - start.startY) * sy,
                ]);
            }
        }
        if (toolset.ink) {
            if (inkStrokeColorInput) {
                inkStrokeColorInput.addEventListener('input', () => {
                    const op = selectedOp();
                    if (op && op.type === 'ink') {
                        pushHistory();
                        op.stroke = inkStrokeColorInput.value;
                        styleOverlay(op);
                        saveDraftSoon();
                    }
                });
            }
            if (inkStrokeWidthInput) {
                inkStrokeWidthInput.addEventListener('change', () => {
                    const v = clampNum(parseFloat(inkStrokeWidthInput.value) || 2, 0.5, 20);
                    inkStrokeWidthInput.value = String(v);
                    const op = selectedOp();
                    if (op && op.type === 'ink') {
                        pushHistory();
                        op.strokeWidth = v;
                        styleOverlay(op);
                        saveDraftSoon();
                    }
                });
            }

            let inkDraft = null; // { points (PDF-pt), previewEl, lastScreenPt, def }
            function inkBBox(points) {
                let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
                points.forEach(([px, py]) => {
                    if (px < minX) minX = px;
                    if (py < minY) minY = py;
                    if (px > maxX) maxX = px;
                    if (py > maxY) maxY = py;
                });
                return { minX, minY, maxX, maxY };
            }
            function renderInkPreview() {
                const b = inkBBox(inkDraft.points);
                const box = {
                    xPx: b.minX * scale, yPx: b.minY * scale,
                    wPx: (b.maxX - b.minX) * scale, hPx: (b.maxY - b.minY) * scale,
                };
                inkDraft.previewEl.style.left = box.xPx + 'px';
                inkDraft.previewEl.style.top = box.yPx + 'px';
                inkDraft.previewEl.style.width = Math.max(1, box.wPx) + 'px';
                inkDraft.previewEl.style.height = Math.max(1, box.hPx) + 'px';
                const old = inkDraft.previewEl.querySelector('svg');
                if (old) old.remove();
                inkDraft.previewEl.appendChild(buildInkSvg({
                    x: b.minX, y: b.minY,
                    w: Math.max(1, b.maxX - b.minX), h: Math.max(1, b.maxY - b.minY),
                    points: inkDraft.points, stroke: inkDraft.def.stroke, strokeWidth: inkDraft.def.strokeWidth,
                }));
            }
            function onInkMove(ev) {
                if (!inkDraft) return;
                ev.preventDefault();
                const rect = pdfCanvas.getBoundingClientRect();
                const sx = ev.clientX - rect.left, sy = ev.clientY - rect.top;
                const last = inkDraft.lastScreenPt;
                const dist = last ? Math.hypot(sx - last[0], sy - last[1]) : Infinity;
                if (dist < INK_MIN_POINT_DIST || inkDraft.points.length >= MAX_INK_POINTS) return;
                inkDraft.points.push([sx / scale, sy / scale]);
                inkDraft.lastScreenPt = [sx, sy];
                renderInkPreview();
            }
            function onInkUp() {
                if (!inkDraft) return;
                window.removeEventListener('pointermove', onInkMove);
                window.removeEventListener('pointerup', onInkUp);
                const points = inkDraft.points;
                const def = inkDraft.def;
                inkDraft.previewEl.remove();
                inkDraft = null;
                if (points.length < 2) return; // a tap, not a stroke: discard, no history push
                const b = inkBBox(points);
                pushHistory();
                const op = {
                    id: nextOpId++, type: 'ink', page: currentPage,
                    x: b.minX, y: b.minY,
                    // Floor at 4pt to match the server serializer's min_value=4
                    // (an axis-aligned freehand stroke is ~0 on one axis).
                    w: Math.max(4, b.maxX - b.minX), h: Math.max(4, b.maxY - b.minY),
                    points, stroke: def.stroke, strokeWidth: def.strokeWidth,
                };
                ops.push(op);
                buildOverlayElement(op);
                setSelected(op.id);
                saveDraftSoon();
            }
            if (pdfCanvas) {
                pdfCanvas.addEventListener('pointerdown', (ev) => {
                    if (mode !== 'ink' || !pdfDoc || ev.target !== pdfCanvas) return;
                    ev.preventDefault();
                    const rect = pdfCanvas.getBoundingClientRect();
                    const sx = ev.clientX - rect.left, sy = ev.clientY - rect.top;
                    const previewEl = document.createElement('div');
                    previewEl.style.position = 'absolute';
                    previewEl.style.pointerEvents = 'none';
                    pdfCanvasContainer.appendChild(previewEl);
                    inkDraft = {
                        points: [[sx / scale, sy / scale]],
                        lastScreenPt: [sx, sy],
                        previewEl,
                        def: inkToolbarDefaults(),
                    };
                    renderInkPreview();
                    window.addEventListener('pointermove', onInkMove);
                    window.addEventListener('pointerup', onInkUp);
                });
            }
        }

        // ---------- Overlay DOM ------------------------------------------------------
        function rebuildOverlays() {
            ops.forEach((o) => {
                if (o.element) { o.element.remove(); o.element = null; }
            });
            ops.forEach((o) => { if (o.page === currentPage) buildOverlayElement(o); });
            ops.forEach((o) => {
                if (o.element) o.element.classList.toggle('ate-selected', o.id === selectedId);
            });
        }

        function styleOverlay(op) {
            const el = op.element;
            if (!el) return;
            el.style.left = (op.x * scale) + 'px';
            el.style.top = (op.y * scale) + 'px';
            el.style.width = (op.w * scale) + 'px';
            el.style.height = (op.h * scale) + 'px';
            if (op.type === 'whiteout') {
                el.style.background = op.color;
            } else if (op.type === 'highlight') {
                el.style.background = op.color;
                el.style.opacity = '0.4';
            } else if (op.type === 'text') {
                const inner = el.querySelector('.ate-text');
                if (inner) {
                    inner.style.fontFamily = FONT_STACKS[op.fontKey] || FONT_STACKS.sans;
                    inner.style.fontSize = (op.fontSize * scale) + 'px';
                    inner.style.color = op.color;
                    inner.style.fontWeight = op.bold ? '700' : '400';
                    inner.style.fontStyle = op.italic ? 'italic' : 'normal';
                    inner.style.textDecoration = op.underline ? 'underline' : 'none';
                    const rtl = ARABIC_RE.test(op.text || '');
                    inner.style.direction = rtl ? 'rtl' : 'ltr';
                    inner.style.textAlign = rtl && op.align === 'left' ? 'right' : op.align;
                }
            } else if (op.type === 'shape') {
                // viewBox is in PDF points (matches op.w/op.h); the SVG's
                // width:100%/height:100% auto-scales it to the div's CSS px
                // size (op.w*scale above), so stroke width scales with zoom
                // for free — no manual *scale multiplication needed here.
                const old = el.querySelector('svg');
                if (old) old.remove();
                el.appendChild(buildShapeSvg(op.shapeKind, op.w, op.h, op.stroke, op.strokeWidth, op.fill, op.fillOpacity));
            } else if (op.type === 'ink') {
                const old = el.querySelector('svg');
                if (old) old.remove();
                el.appendChild(buildInkSvg(op));
            }
        }

        function buildOverlayElement(op) {
            const el = document.createElement('div');
            el.className = 'ate-overlay';
            el.style.position = 'absolute';
            el.style.boxSizing = 'border-box';
            el.style.touchAction = 'none';
            el.style.userSelect = 'none';
            el.style.cursor = 'move';

            if (op.type === 'text') {
                const inner = document.createElement('div');
                inner.className = 'ate-text';
                inner.contentEditable = 'false';
                inner.spellcheck = false;
                inner.style.width = '100%';
                inner.style.height = '100%';
                inner.style.overflow = 'hidden';
                inner.style.lineHeight = '1.25';
                inner.style.outline = 'none';
                inner.style.whiteSpace = 'pre-wrap';
                inner.style.wordBreak = 'break-word';
                inner.textContent = op.text || '';
                el.appendChild(inner);

                el.addEventListener('dblclick', (ev) => {
                    ev.stopPropagation();
                    focusTextEditing(op);
                });
            } else if (op.type === 'image' || op.type === 'signature') {
                const img = document.createElement('img');
                img.src = op.imageDataUri;
                img.alt = '';
                img.draggable = false;
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.display = 'block';
                img.style.pointerEvents = 'none';
                el.appendChild(img);
            }

            // Delete button
            const del = document.createElement('button');
            del.type = 'button';
            del.className = 'ate-del';
            del.setAttribute('aria-label', t('DELETE_OBJECT_LABEL', 'Delete'));
            del.textContent = '×';
            del.addEventListener('click', (ev) => {
                ev.stopPropagation();
                pushHistory();
                const idx = ops.findIndex((o) => o.id === op.id);
                if (idx >= 0) ops.splice(idx, 1);
                el.remove();
                if (selectedId === op.id) setSelected(null);
                saveDraftSoon();
            });
            el.appendChild(del);

            // Corner resize handle (free resize for boxes)
            const handle = document.createElement('div');
            handle.className = 'ate-handle';
            el.appendChild(handle);

            attachDragAndResize(op, el, handle, op.type === 'ink' ? inkGeomHook : null);

            el.addEventListener('pointerdown', () => setSelected(op.id));

            op.element = el;
            pdfCanvasContainer.appendChild(el);
            styleOverlay(op);
        }

        function focusTextEditing(op) {
            const inner = op.element && op.element.querySelector('.ate-text');
            if (!inner) return;
            inner.contentEditable = 'plaintext-only' in document.body ? 'plaintext-only' : 'true';
            // Some browsers reject 'plaintext-only' assignment via property; normalize.
            try { inner.contentEditable = 'plaintext-only'; } catch (_) { inner.contentEditable = 'true'; }
            inner.style.cursor = 'text';
            op.element.style.cursor = 'auto';
            inner.focus();
            const sel = window.getSelection();
            if (sel && inner.lastChild) {
                const range = document.createRange();
                range.selectNodeContents(inner);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            }
            if (!inner.dataset.ateHooked) {
                inner.dataset.ateHooked = '1';
                let editSnapshot = null;
                inner.addEventListener('focus', () => {
                    editSnapshot = JSON.stringify(serializeOps());
                });
                inner.addEventListener('input', () => {
                    op.text = inner.innerText.replace(/ /g, ' ');
                    styleOverlay(op); // direction may flip to rtl as the user types
                    saveDraftSoon();
                });
                inner.addEventListener('blur', () => {
                    inner.contentEditable = 'false';
                    inner.style.cursor = '';
                    op.element.style.cursor = 'move';
                    if (editSnapshot !== null && editSnapshot !== JSON.stringify(serializeOps())) {
                        undoStack.push(editSnapshot);
                        redoStack.length = 0;
                        updateHistoryButtons();
                    }
                    editSnapshot = null;
                });
                inner.addEventListener('keydown', (ev) => {
                    ev.stopPropagation(); // keep Delete/arrows from firing object shortcuts
                    if (ev.key === 'Escape') inner.blur();
                });
            }
        }

        function attachDragAndResize(op, el, handle, onGeom) {
            let dragMode = null;
            let startClientX = 0, startClientY = 0;
            let startX = 0, startY = 0, startW = 0, startH = 0;
            let moved = false;
            let snapshot = null;

            function clampToPage() {
                const pageW = pdfCanvas.width / scale;
                const pageH = pdfCanvas.height / scale;
                op.x = Math.max(0, Math.min(op.x, pageW - 8));
                op.y = Math.max(0, Math.min(op.y, pageH - 8));
                op.w = Math.max(8, Math.min(op.w, pageW - op.x));
                op.h = Math.max(8, Math.min(op.h, pageH - op.y));
            }

            function onPointerMove(ev) {
                if (!dragMode) return;
                ev.preventDefault();
                const dx = (ev.clientX - startClientX) / scale;
                const dy = (ev.clientY - startClientY) / scale;
                if (dx || dy) moved = true;
                if (dragMode === 'drag') {
                    op.x = startX + dx;
                    op.y = startY + dy;
                } else {
                    op.w = startW + dx;
                    op.h = startH + dy;
                }
                clampToPage();
                // Let type-specific geometry (e.g. ink's absolute points, which the
                // backend draws verbatim and independently of x/y/w/h) stay in sync
                // with the box attachDragAndResize just moved/resized.
                if (onGeom) onGeom(dragMode, op, { startX, startY, startW, startH });
                styleOverlay(op);
            }
            function onPointerUp() {
                if (onGeom) onGeom('end', op, { startX, startY, startW, startH });
                if (moved && snapshot !== null) {
                    undoStack.push(snapshot);
                    redoStack.length = 0;
                    updateHistoryButtons();
                    saveDraftSoon();
                }
                dragMode = null;
                snapshot = null;
                window.removeEventListener('pointermove', onPointerMove);
                window.removeEventListener('pointerup', onPointerUp);
                window.removeEventListener('pointercancel', onPointerUp);
            }
            function begin(ev, m) {
                ev.preventDefault();
                dragMode = m;
                moved = false;
                snapshot = JSON.stringify(serializeOps());
                startClientX = ev.clientX;
                startClientY = ev.clientY;
                startX = op.x; startY = op.y; startW = op.w; startH = op.h;
                if (onGeom) onGeom('begin', op, { startX, startY, startW, startH });
                window.addEventListener('pointermove', onPointerMove);
                window.addEventListener('pointerup', onPointerUp);
                window.addEventListener('pointercancel', onPointerUp);
            }

            el.addEventListener('pointerdown', (ev) => {
                if (ev.target === handle || ev.target.tagName === 'BUTTON') return;
                if (ev.target.classList && ev.target.classList.contains('ate-text')
                    && ev.target.isContentEditable) return; // editing: let the caret work
                begin(ev, 'drag');
            });
            handle.addEventListener('pointerdown', (ev) => {
                ev.stopPropagation();
                begin(ev, 'resize');
            });
        }

        // ---------- Keyboard shortcuts ----------------------------------------------
        document.addEventListener('keydown', (ev) => {
            const target = ev.target;
            if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
            const op = selectedOp();
            if ((ev.ctrlKey || ev.metaKey) && !ev.shiftKey && ev.key.toLowerCase() === 'z') {
                ev.preventDefault(); undo(); return;
            }
            if ((ev.ctrlKey || ev.metaKey) && (ev.key.toLowerCase() === 'y' || (ev.shiftKey && ev.key.toLowerCase() === 'z'))) {
                ev.preventDefault(); redo(); return;
            }
            if (!op) return;
            if (ev.key === 'Delete' || ev.key === 'Backspace') {
                ev.preventDefault();
                pushHistory();
                const idx = ops.findIndex((o) => o.id === op.id);
                if (idx >= 0) {
                    ops[idx].element && ops[idx].element.remove();
                    ops.splice(idx, 1);
                }
                setSelected(null);
                saveDraftSoon();
                return;
            }
            if (ev.key === 'Escape') { setSelected(null); return; }
            const step = ev.shiftKey ? 10 : 1;
            const nudge = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[ev.key];
            if (nudge) {
                ev.preventDefault();
                const newX = Math.max(0, op.x + nudge[0]);
                const newY = Math.max(0, op.y + nudge[1]);
                if (op.type === 'ink' && op.points) {
                    // Keyboard nudge bypasses attachDragAndResize's onGeom hook —
                    // shift ink's absolute points by the same clamped delta so the
                    // materialized stroke doesn't lag behind the moved box.
                    const dx = newX - op.x, dy = newY - op.y;
                    op.points = op.points.map(([px, py]) => [px + dx, py + dy]);
                }
                op.x = newX;
                op.y = newY;
                styleOverlay(op);
                saveDraftSoon();
            }
        });

        // ---------- File input hook ---------------------------------------------------
        function hookFileInput(input) {
            if (!input) return;
            input.addEventListener('change', () => {
                const f = input.files && input.files[0];
                if (f) handleFileSelected(f);
            });
        }
        hookFileInput(fileInput);
        hookFileInput(fileInputDrop);

        // ---------- Op -> API payload serialization ------------------------------------
        function opToPayload(o) {
            const base = {
                type: o.type,
                page: o.page - 1, // 0-indexed for backend
                x: +o.x.toFixed(2),
                y: +o.y.toFixed(2),
                width: +o.w.toFixed(2),
                height: +o.h.toFixed(2),
                color: o.color,
            };
            if (o.type === 'text') {
                base.text = o.text;
                base.font_key = o.fontKey;
                base.font_size = o.fontSize;
                base.bold = !!o.bold;
                base.italic = !!o.italic;
                base.underline = !!o.underline;
                base.align = o.align;
            } else if (o.type === 'image' || o.type === 'signature') {
                delete base.color;
                base.image_data_uri = o.imageDataUri;
            } else if (o.type === 'shape') {
                delete base.color;
                base.shape_kind = o.shapeKind;
                base.stroke = o.stroke;
                base.stroke_width = o.strokeWidth;
                base.fill = o.fill;
                base.fill_opacity = o.fillOpacity;
            } else if (o.type === 'ink') {
                delete base.color;
                base.points = o.points;
                base.stroke = o.stroke;
                base.stroke_width = o.strokeWidth;
            }
            return base;
        }

        // ---------- Form submit ---------------------------------------------------------
        form.addEventListener('submit', async (ev) => {
            ev.preventDefault();

            const selectedFiles = (fileInput?.files && fileInput.files.length > 0)
                ? fileInput.files
                : (fileInputDrop?.files && fileInputDrop.files.length > 0)
                    ? fileInputDrop.files
                    : null;
            const selectedFile = selectedFiles?.[0] || null;
            if (!selectedFile) {
                window.showError && window.showError(
                    t('SELECT_FILE_MESSAGE', 'Please select a PDF first.'), 'editorResult'
                );
                return;
            }

            const payload = ops
                .filter((o) => o.type !== 'text' || (o.text || '').trim().length > 0)
                .map(opToPayload);
            if (payload.length === 0) {
                window.showError && window.showError(
                    t('NO_OBJECTS_MESSAGE', 'Click on the page to add text first.'), 'editorResult'
                );
                return;
            }

            const formData = new FormData();
            formData.append(window.FILE_INPUT_NAME || 'pdf_file', selectedFile);
            formData.append('operations', JSON.stringify(payload));

            window.showLoading && window.showLoading('loadingContainer', { showProgress: true });
            submitButton && (submitButton.disabled = true);

            const abortController = new AbortController();
            window._currentAbortController = abortController;
            window._onCancelCallback = () => {
                window.hideLoading && window.hideLoading('loadingContainer');
                submitButton && (submitButton.disabled = false);
            };

            try {
                const init = await (window.ConvertiaWebToken
                    ? window.ConvertiaWebToken.attachToken({
                        method: 'POST', body: formData,
                        headers: { 'X-CSRFToken': window.CSRF_TOKEN },
                        signal: abortController.signal,
                      })
                    : Promise.resolve({
                        method: 'POST', body: formData,
                        headers: { 'X-CSRFToken': window.CSRF_TOKEN },
                        signal: abortController.signal,
                      }));
                const response = await fetch(apiUrl, init);
                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    if (errData && errData.captcha_required && window.ensureTurnstileWidget) {
                        window.ensureTurnstileWidget();
                    }
                    throw new Error(errData.error || errData.detail || 'Editing failed.');
                }
                const blob = await response.blob();
                window.hideLoading && window.hideLoading('loadingContainer');
                try { draftKey && sessionStorage.removeItem(draftKey); } catch (_) { /* ignore */ }
                window.showDownloadButton && window.showDownloadButton(
                    blob, selectedFile.name, 'downloadContainer',
                    {
                        successTitle: t('SUCCESS_TITLE', 'Editing complete!'),
                        downloadButtonText: t('DOWNLOAD_BUTTON_TEXT', 'Download File'),
                        convertAnotherText: t('EDIT_ANOTHER_TEXT', 'Edit another file'),
                        onConvertAnother: () => window.location.reload(),
                    }
                );
            } catch (err) {
                if (err && err.name === 'AbortError') return;
                window.hideLoading && window.hideLoading('loadingContainer');
                submitButton && (submitButton.disabled = false);
                window.showError && window.showError(
                    err.message || t('ERROR_MESSAGE', 'Editing failed.'), 'editorResult'
                );
            }
        });
    }

    window.initPdfEditor = initPdfEditor;
})();
