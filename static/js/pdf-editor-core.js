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
 * The overlay model supports 8 op types. text/whiteout/highlight are fully
 * wired (click-to-place + submit serialization). image/signature/shape/ink
 * are accepted by the model and submit serializer now (so a future task can
 * add the UI that creates them) but nothing yet creates them:
 *   image/signature: {type,page,x,y,width,height,image_data_uri}
 *   shape:           {type,page,x,y,width,height,shape_kind,stroke,stroke_width,fill,fill_opacity}
 *   ink:             {type,page,x,y,width,height,points:[[x,y]...],stroke,stroke_width}
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

        const FONT_STACKS = {
            sans: "'Noto Sans', 'Segoe UI', Arial, sans-serif",
            serif: "'Noto Serif', Georgia, 'Times New Roman', serif",
            mono: "'Noto Sans Mono', 'Courier New', monospace",
        };
        const ARABIC_RE = /[؀-ۿݐ-ݿ]/;
        const HIGHLIGHT_DEFAULT = '#ffee00';

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
                const rect = pdfCanvas.getBoundingClientRect();
                const px = ev.clientX - rect.left;
                const py = ev.clientY - rect.top;
                const x = px / scale;
                const y = py / scale;

                pushHistory();
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
                } else if (toolset.text) {
                    const d = toolbarDefaults();
                    op = {
                        id: nextOpId++, type: 'text', page: currentPage,
                        x: x - 10, y: y - d.fontSize * 0.8, w: 220, h: Math.max(28, d.fontSize * 2),
                        text: '', ...d,
                    };
                } else {
                    return;
                }
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

            attachDragAndResize(op, el, handle);

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

        function attachDragAndResize(op, el, handle) {
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
                styleOverlay(op);
            }
            function onPointerUp() {
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
                op.x = Math.max(0, op.x + nudge[0]);
                op.y = Math.max(0, op.y + nudge[1]);
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
