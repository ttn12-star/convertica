/**
 * Sign PDF Editor
 *
 * Three-tab signature creator (Draw / Type / Upload) plus a PDF.js preview
 * where the user clicks to place signatures, drags to position them, and
 * pulls corner handles to resize. Multiple signatures are supported across
 * multiple pages; on submit, each placement is serialised as PDF points
 * and sent to /api/pdf-edit/sign/.
 *
 * Reuses window helpers: showLoading, hideLoading, showError, showDownloadButton,
 * CSRF_TOKEN, API_URL, FILE_INPUT_NAME — same conventions as the watermark editor.
 */
document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    // ---------- PDF.js loader (mirrors pdf-watermark-editor.js) ---------------
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
    const settingsSection = document.getElementById('signSettingsSection');
    const pdfCanvas = document.getElementById('pdfCanvas');
    const pdfCanvasContainer = document.getElementById('pdfCanvasContainer');
    const pageSelector = document.getElementById('pageSelector');
    const submitButton = document.getElementById('editButton');
    const placementHint = document.getElementById('placementHint');

    // Signature panel
    const tabButtons = document.querySelectorAll('[data-sig-tab]');
    const tabPanels = {
        draw: document.getElementById('sigTabDraw'),
        type: document.getElementById('sigTabType'),
        upload: document.getElementById('sigTabUpload'),
    };
    const drawCanvas = document.getElementById('signatureDrawCanvas');
    const drawClearBtn = document.getElementById('signatureDrawClear');
    const typeInput = document.getElementById('signatureTypeText');
    const typePreviewCanvas = document.getElementById('signatureTypePreview');
    const uploadInput = document.getElementById('signatureUploadInput');
    const uploadButton = document.getElementById('signatureUploadButton');
    const uploadFileName = document.getElementById('signatureUploadFileName');
    const applySignatureBtn = document.getElementById('applySignature');
    const useSavedSignatureBtn = document.getElementById('useSavedSignature');
    const activeSignaturePreview = document.getElementById('activeSignaturePreview');
    const activeSignatureImg = document.getElementById('activeSignatureImg');

    // ---------- State --------------------------------------------------------
    const STORAGE_KEY = 'convertica_signature_v1';
    let pdfDoc = null;
    let pageCount = 0;
    let currentPage = 1; // 1-indexed for UI; converted to 0-indexed at submit
    let scale = 1.0;     // CSS pixels per PDF point at the current render
    let pdfPageWidth = 0;
    let pdfPageHeight = 0;
    let currentRenderTask = null;
    let activeSignatureImage = null; // data URI of the signature awaiting placement
    let nextSigId = 1;
    /** placedSignatures: array of {
     *    id, page (1-indexed for state, converted at submit),
     *    xPx, yPx, wPx, hPx (CSS pixels relative to canvas),
     *    image (data URI),
     *    element (the absolutely-positioned DOM overlay; only built for current page)
     * }
     */
    const placedSignatures = [];

    // ---------- Tab switching ------------------------------------------------
    function setActiveTab(tabName) {
        tabButtons.forEach((btn) => {
            const active = btn.dataset.sigTab === tabName;
            btn.classList.toggle('border-blue-600', active);
            btn.classList.toggle('text-blue-600', active);
            btn.classList.toggle('border-transparent', !active);
            btn.classList.toggle('text-gray-500', !active);
        });
        Object.entries(tabPanels).forEach(([name, panel]) => {
            if (!panel) return;
            panel.classList.toggle('hidden', name !== tabName);
        });
    }
    tabButtons.forEach((btn) => {
        btn.addEventListener('click', () => setActiveTab(btn.dataset.sigTab));
    });
    setActiveTab('draw');

    // ---------- Draw tab: capture strokes on a canvas ------------------------
    (function initDrawCanvas() {
        if (!drawCanvas) return;
        const ctx = drawCanvas.getContext('2d');
        let drawing = false;
        let lastX = 0;
        let lastY = 0;

        function paintBackground() {
            // Transparent background; subtle baseline guide.
            ctx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
            ctx.save();
            ctx.strokeStyle = '#e5e7eb';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(20, drawCanvas.height - 30);
            ctx.lineTo(drawCanvas.width - 20, drawCanvas.height - 30);
            ctx.stroke();
            ctx.restore();
        }
        paintBackground();

        function pointFromEvent(ev) {
            const rect = drawCanvas.getBoundingClientRect();
            const x = (ev.clientX - rect.left) * (drawCanvas.width / rect.width);
            const y = (ev.clientY - rect.top) * (drawCanvas.height / rect.height);
            return { x, y };
        }

        function begin(ev) {
            ev.preventDefault();
            drawing = true;
            const p = pointFromEvent(ev);
            lastX = p.x;
            lastY = p.y;
        }
        function move(ev) {
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
            lastX = p.x;
            lastY = p.y;
        }
        function end(ev) {
            if (!drawing) return;
            ev.preventDefault();
            drawing = false;
        }

        drawCanvas.addEventListener('pointerdown', begin);
        drawCanvas.addEventListener('pointermove', move);
        drawCanvas.addEventListener('pointerup', end);
        drawCanvas.addEventListener('pointerleave', end);
        drawCanvas.addEventListener('pointercancel', end);

        if (drawClearBtn) {
            drawClearBtn.addEventListener('click', () => paintBackground());
        }
        // Mark canvas as having transparent strokes so the background stays empty
        drawCanvas.dataset.exportTransparent = 'true';
    })();

    // ---------- Type tab: render typed name into the preview canvas ----------
    function renderTypedSignature() {
        if (!typeInput || !typePreviewCanvas) return;
        const text = (typeInput.value || '').trim();
        const ctx = typePreviewCanvas.getContext('2d');
        ctx.clearRect(0, 0, typePreviewCanvas.width, typePreviewCanvas.height);
        if (!text) return;

        // Fit the text within the canvas; shrink font if needed.
        let fontSize = 64;
        ctx.fillStyle = '#111827';
        do {
            ctx.font = `${fontSize}px "Caveat", "Brush Script MT", cursive`;
            if (ctx.measureText(text).width <= typePreviewCanvas.width - 30) break;
            fontSize -= 2;
        } while (fontSize > 20);

        ctx.textBaseline = 'middle';
        ctx.fillText(text, 15, typePreviewCanvas.height / 2);
    }
    if (typeInput) typeInput.addEventListener('input', renderTypedSignature);

    // ---------- Upload tab: file → data URI ----------------------------------
    let uploadedSignatureDataUri = null;
    if (uploadButton && uploadInput) {
        uploadButton.addEventListener('click', () => uploadInput.click());
    }
    if (uploadInput) {
        uploadInput.addEventListener('change', () => {
            const file = uploadInput.files && uploadInput.files[0];
            if (!file) return;
            if (uploadFileName) uploadFileName.textContent = file.name;
            const reader = new FileReader();
            reader.onload = () => { uploadedSignatureDataUri = String(reader.result || ''); };
            reader.readAsDataURL(file);
        });
    }

    // ---------- Build an active signature (depends on the open tab) ----------
    function activeTab() {
        for (const btn of tabButtons) {
            if (btn.classList.contains('text-blue-600')) return btn.dataset.sigTab;
        }
        return 'draw';
    }

    function exportCanvasAsPng(canvas) {
        // Re-render with transparent background by copying to an off-screen canvas
        // and trimming a bit. Simpler: rely on the canvas already being transparent.
        return canvas.toDataURL('image/png');
    }

    function buildActiveSignature() {
        const tab = activeTab();
        if (tab === 'draw') {
            return exportCanvasAsPng(drawCanvas);
        }
        if (tab === 'type') {
            renderTypedSignature();
            return exportCanvasAsPng(typePreviewCanvas);
        }
        if (tab === 'upload') {
            return uploadedSignatureDataUri;
        }
        return null;
    }

    function setActiveSignature(dataUri) {
        activeSignatureImage = dataUri || null;
        if (activeSignaturePreview && activeSignatureImg) {
            if (dataUri) {
                activeSignatureImg.src = dataUri;
                activeSignaturePreview.classList.remove('hidden');
            } else {
                activeSignaturePreview.classList.add('hidden');
            }
        }
        if (placementHint) {
            placementHint.classList.toggle('hidden', !dataUri);
        }
        if (pdfCanvas) {
            pdfCanvas.style.cursor = dataUri ? 'crosshair' : 'default';
        }
    }

    if (applySignatureBtn) {
        applySignatureBtn.addEventListener('click', () => {
            const dataUri = buildActiveSignature();
            if (!dataUri || dataUri.length < 100) {
                window.showError && window.showError(
                    'Please draw, type, or upload a signature first.',
                    'editorResult'
                );
                return;
            }
            setActiveSignature(dataUri);
            try { localStorage.setItem(STORAGE_KEY, dataUri); } catch (_) { /* quota; ignore */ }
            // Show "Use saved signature" on next page load (button is rendered already)
            updateSavedSignatureButton();
        });
    }

    function updateSavedSignatureButton() {
        if (!useSavedSignatureBtn) return;
        let saved = null;
        try { saved = localStorage.getItem(STORAGE_KEY); } catch (_) { /* ignore */ }
        useSavedSignatureBtn.classList.toggle('hidden', !saved);
    }
    if (useSavedSignatureBtn) {
        useSavedSignatureBtn.addEventListener('click', () => {
            let saved = null;
            try { saved = localStorage.getItem(STORAGE_KEY); } catch (_) { /* ignore */ }
            if (saved) setActiveSignature(saved);
        });
    }
    updateSavedSignatureButton();

    // ---------- PDF load + render -------------------------------------------
    async function handleFileSelected(file) {
        if (!file) return;
        const ok = await ensurePdfJsLoaded();
        if (!ok) {
            window.showError && window.showError(
                window.FAILED_TO_LOAD_PDF || 'Failed to load PDF preview.',
                'editorResult'
            );
            return;
        }
        cleanupPreviousPDF();
        try {
            const arrayBuf = await file.arrayBuffer();
            pdfDoc = await window.pdfjsLib.getDocument({
                data: arrayBuf,
                disableAutoFetch: true,
                disableStream: true,
            }).promise;
        } catch (e) {
            window.showError && window.showError(
                window.FAILED_TO_LOAD_PDF || 'Failed to load PDF preview.',
                'editorResult'
            );
            return;
        }
        pageCount = pdfDoc.numPages;
        currentPage = 1;
        populatePageSelector();
        await renderPage(currentPage);
        previewSection && previewSection.classList.remove('hidden');
        settingsSection && settingsSection.classList.remove('hidden');
        submitButton && (submitButton.disabled = false);
    }

    function cleanupPreviousPDF() {
        if (pdfDoc) {
            try { pdfDoc.destroy(); } catch (_) { /* ignore */ }
            pdfDoc = null;
        }
        pageCount = 0;
        currentPage = 1;
        placedSignatures.forEach((s) => { if (s.element) s.element.remove(); });
        placedSignatures.length = 0;
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
            opt.textContent = (window.PAGE_LABEL || 'Page') + ' ' + i + ' / ' + pageCount;
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
                rerenderOverlaysForCurrentPage();
            }
        });
    }

    async function renderPage(pageNum) {
        if (!pdfDoc) return;
        const page = await pdfDoc.getPage(pageNum);
        const baseViewport = page.getViewport({ scale: 1.0 });

        const maxWidth = 600;
        const maxHeight = 700;
        const widthScale = maxWidth / baseViewport.width;
        const heightScale = maxHeight / baseViewport.height;
        scale = Math.min(widthScale, heightScale, 1.0);
        const scaledViewport = page.getViewport({ scale });

        pdfCanvas.width = scaledViewport.width;
        pdfCanvas.height = scaledViewport.height;
        pdfCanvas.style.width = '';
        pdfCanvas.style.height = '';
        pdfPageWidth = baseViewport.width;
        pdfPageHeight = baseViewport.height;

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
    }

    // ---------- Placement: click on canvas → drop signature ------------------
    if (pdfCanvas) {
        pdfCanvas.addEventListener('click', (ev) => {
            if (!activeSignatureImage) return;
            const rect = pdfCanvas.getBoundingClientRect();
            const px = ev.clientX - rect.left;
            const py = ev.clientY - rect.top;
            // Default signature size: 150pt wide, height kept by image's natural ratio.
            const wPx = 150 * scale;
            const tmp = new Image();
            tmp.onload = () => {
                const aspect = tmp.height / tmp.width || 0.4;
                const hPx = wPx * aspect;
                const xPx = Math.max(0, px - wPx / 2);
                const yPx = Math.max(0, py - hPx / 2);
                addPlacedSignature(activeSignatureImage, xPx, yPx, wPx, hPx);
            };
            tmp.src = activeSignatureImage;
        });
    }

    function rerenderOverlaysForCurrentPage() {
        // Remove all overlay DOM nodes; rebuild for the current page only.
        placedSignatures.forEach((s) => {
            if (s.element) {
                s.element.remove();
                s.element = null;
            }
        });
        placedSignatures.forEach((s) => {
            if (s.page === currentPage) {
                buildOverlayElement(s);
            }
        });
    }

    function addPlacedSignature(image, xPx, yPx, wPx, hPx) {
        const sig = {
            id: nextSigId++,
            page: currentPage,
            xPx, yPx, wPx, hPx,
            image,
            element: null,
        };
        placedSignatures.push(sig);
        buildOverlayElement(sig);
    }

    function buildOverlayElement(sig) {
        const el = document.createElement('div');
        el.className = 'signature-overlay';
        el.style.position = 'absolute';
        el.style.left = sig.xPx + 'px';
        el.style.top = sig.yPx + 'px';
        el.style.width = sig.wPx + 'px';
        el.style.height = sig.hPx + 'px';
        el.style.cursor = 'move';
        el.style.touchAction = 'none';
        el.style.border = '1px dashed rgba(37, 99, 235, 0.7)';
        el.style.backgroundImage = `url("${sig.image}")`;
        el.style.backgroundRepeat = 'no-repeat';
        el.style.backgroundSize = '100% 100%';
        el.style.userSelect = 'none';

        // Delete button
        const del = document.createElement('button');
        del.type = 'button';
        del.setAttribute('aria-label', 'Delete signature');
        del.textContent = '×';
        del.style.position = 'absolute';
        del.style.top = '-10px';
        del.style.right = '-10px';
        del.style.width = '22px';
        del.style.height = '22px';
        del.style.borderRadius = '50%';
        del.style.background = '#ef4444';
        del.style.color = 'white';
        del.style.border = '2px solid white';
        del.style.fontWeight = 'bold';
        del.style.cursor = 'pointer';
        del.style.lineHeight = '1';
        del.style.zIndex = '20';
        del.addEventListener('click', (ev) => {
            ev.stopPropagation();
            const idx = placedSignatures.findIndex((s) => s.id === sig.id);
            if (idx >= 0) placedSignatures.splice(idx, 1);
            el.remove();
        });
        el.appendChild(del);

        // Corner resize handle (south-east, proportional)
        const handle = document.createElement('div');
        handle.style.position = 'absolute';
        handle.style.right = '-9px';
        handle.style.bottom = '-9px';
        handle.style.width = '18px';
        handle.style.height = '18px';
        handle.style.borderRadius = '50%';
        handle.style.background = 'linear-gradient(135deg, #3b82f6 0%, #10b981 100%)';
        handle.style.border = '3px solid white';
        handle.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
        handle.style.cursor = 'nwse-resize';
        handle.style.touchAction = 'none';
        handle.style.zIndex = '15';
        el.appendChild(handle);

        attachDragAndResize(sig, el, handle);

        sig.element = el;
        pdfCanvasContainer.appendChild(el);
    }

    function attachDragAndResize(sig, el, handle) {
        let mode = null; // 'drag' or 'resize'
        let startClientX = 0;
        let startClientY = 0;
        let startLeft = 0;
        let startTop = 0;
        let startW = 0;
        let startH = 0;
        let aspect = 1;

        function clampToCanvas() {
            const cw = pdfCanvas.width;
            const ch = pdfCanvas.height;
            sig.xPx = Math.max(0, Math.min(sig.xPx, cw - 10));
            sig.yPx = Math.max(0, Math.min(sig.yPx, ch - 10));
            sig.wPx = Math.max(20, Math.min(sig.wPx, cw - sig.xPx));
            sig.hPx = Math.max(10, Math.min(sig.hPx, ch - sig.yPx));
        }

        function applyToElement() {
            el.style.left = sig.xPx + 'px';
            el.style.top = sig.yPx + 'px';
            el.style.width = sig.wPx + 'px';
            el.style.height = sig.hPx + 'px';
        }

        function onPointerMove(ev) {
            if (!mode) return;
            ev.preventDefault();
            const dx = ev.clientX - startClientX;
            const dy = ev.clientY - startClientY;
            if (mode === 'drag') {
                sig.xPx = startLeft + dx;
                sig.yPx = startTop + dy;
            } else if (mode === 'resize') {
                // Proportional resize from SE corner: drive by larger axis.
                const newW = Math.max(20, startW + dx);
                const newH = Math.max(10, newW * aspect);
                sig.wPx = newW;
                sig.hPx = newH;
            }
            clampToCanvas();
            applyToElement();
        }
        function onPointerUp() {
            mode = null;
            window.removeEventListener('pointermove', onPointerMove);
            window.removeEventListener('pointerup', onPointerUp);
            window.removeEventListener('pointercancel', onPointerUp);
        }

        el.addEventListener('pointerdown', (ev) => {
            if (ev.target === handle) return; // resize handled below
            if (ev.target.tagName === 'BUTTON') return; // delete
            ev.preventDefault();
            mode = 'drag';
            startClientX = ev.clientX;
            startClientY = ev.clientY;
            startLeft = sig.xPx;
            startTop = sig.yPx;
            window.addEventListener('pointermove', onPointerMove);
            window.addEventListener('pointerup', onPointerUp);
            window.addEventListener('pointercancel', onPointerUp);
        });
        handle.addEventListener('pointerdown', (ev) => {
            ev.stopPropagation();
            ev.preventDefault();
            mode = 'resize';
            startClientX = ev.clientX;
            startClientY = ev.clientY;
            startW = sig.wPx;
            startH = sig.hPx;
            aspect = sig.hPx / sig.wPx || 1;
            window.addEventListener('pointermove', onPointerMove);
            window.addEventListener('pointerup', onPointerUp);
            window.addEventListener('pointercancel', onPointerUp);
        });
    }

    // ---------- File input hook ----------------------------------------------
    function hookFileInput(input) {
        if (!input) return;
        input.addEventListener('change', () => {
            const f = input.files && input.files[0];
            if (f) handleFileSelected(f);
        });
    }
    hookFileInput(fileInput);
    hookFileInput(fileInputDrop);

    // ---------- Form submit --------------------------------------------------
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
                window.SELECT_FILE_MESSAGE || 'Please select a PDF first.',
                'editorResult'
            );
            return;
        }
        if (placedSignatures.length === 0) {
            window.showError && window.showError(
                'Please create a signature and click on the PDF to place it.',
                'editorResult'
            );
            return;
        }

        // Serialise placements as PDF points (top-left origin).
        const payload = placedSignatures.map((s) => ({
            page: s.page - 1, // 0-indexed for backend
            x: +(s.xPx / scale).toFixed(2),
            y: +(s.yPx / scale).toFixed(2),
            width: +(s.wPx / scale).toFixed(2),
            height: +(s.hPx / scale).toFixed(2),
            image_data_uri: s.image,
        }));

        const formData = new FormData();
        formData.append(window.FILE_INPUT_NAME || 'pdf_file', selectedFile);
        formData.append('signatures', JSON.stringify(payload));

        window.showLoading && window.showLoading('loadingContainer', { showProgress: true });
        submitButton && (submitButton.disabled = true);

        const abortController = new AbortController();
        window._currentAbortController = abortController;
        window._onCancelCallback = () => {
            window.hideLoading && window.hideLoading('loadingContainer');
            submitButton && (submitButton.disabled = false);
        };

        try {
            const response = await fetch(window.API_URL, {
                method: 'POST',
                headers: { 'X-CSRFToken': window.CSRF_TOKEN },
                body: formData,
                signal: abortController.signal,
            });
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || errData.detail || 'Signing failed.');
            }
            const blob = await response.blob();
            window.hideLoading && window.hideLoading('loadingContainer');
            const cd = response.headers.get('content-disposition') || '';
            let downloadName = selectedFile.name.replace(/\.pdf$/i, '') + '_signed.pdf';
            const m = cd.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (m && m[1]) downloadName = m[1].replace(/['"]/g, '');
            window.showDownloadButton && window.showDownloadButton(
                blob, downloadName, 'downloadContainer',
                {
                    successTitle: window.SUCCESS_TITLE || 'Signing Complete!',
                    downloadButtonText: window.DOWNLOAD_BUTTON_TEXT || 'Download File',
                    convertAnotherText: window.EDIT_ANOTHER_TEXT || 'Sign another file',
                    onConvertAnother: () => window.location.reload(),
                }
            );
        } catch (err) {
            if (err && err.name === 'AbortError') return;
            window.hideLoading && window.hideLoading('loadingContainer');
            submitButton && (submitButton.disabled = false);
            window.showError && window.showError(
                err.message || (window.ERROR_MESSAGE || 'Signing failed.'),
                'editorResult'
            );
        }
    });
});
