/**
 * PDF Crop Editor Component
 * Visual PDF cropping with drag & drop selection
 */
document.addEventListener('DOMContentLoaded', () => {
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
                existing.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
                return;
            }

            const script = document.createElement('script');
            script.src = src;
            script.async = true;
            script.crossOrigin = 'anonymous';
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`Failed to load ${src}`));
            document.head.appendChild(script);
        });
    }

    async function ensurePdfJsLoaded() {
        if (typeof window.pdfjsLib !== 'undefined') return true;

        for (const src of PDFJS_CANDIDATES) {
            try {
                await loadExternalScript(src);
                if (typeof window.pdfjsLib !== 'undefined') break;
            } catch (e) {
                // try next
            }
        }

        if (typeof window.pdfjsLib === 'undefined') return false;

        if (!window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
            window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CANDIDATES[0];
        }

        return true;
    }

    // Set up PDF.js worker (best-effort)
    if (typeof window.pdfjsLib !== 'undefined') {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CANDIDATES[0];
    }

    const form = document.getElementById('editorForm');
    if (!form) return;

    const fileInput = document.getElementById('fileInput');
    const fileInputDrop = document.getElementById('fileInputDrop');
    const selectFileButton = document.getElementById('selectFileButton');
    const pdfPreviewSection = document.getElementById('pdfPreviewSection');
    const pdfCanvas = document.getElementById('pdfCanvas');
    const pdfCanvasContainer = document.getElementById('pdfCanvasContainer');
    const cropSelection = document.getElementById('cropSelection');
    const cropOverlay = document.getElementById('cropOverlay');
    const cropOverlayTop = document.getElementById('cropOverlayTop');
    const cropOverlayRight = document.getElementById('cropOverlayRight');
    const cropOverlayBottom = document.getElementById('cropOverlayBottom');
    const cropOverlayLeft = document.getElementById('cropOverlayLeft');
    const cropReadyIndicator = document.getElementById('cropReadyIndicator');
    const pageSelector = document.getElementById('pageSelector');
    const editButton = document.getElementById('editButton');
    const resultContainer = document.getElementById('editorResult');

    // State
    let pdfDoc = null;
    let currentPage = 1;
    let pageCount = 0;
    let scale = 1.0;
    let pdfPageWidth = 0;
    let pdfPageHeight = 0;
    let canvasWidth = 0;
    let canvasHeight = 0;
    let currentSelection = null;
    let isSelecting = false; // True when dragging to create new selection
    let selectionStartX = 0; // X coordinate when starting selection
    let selectionStartY = 0; // Y coordinate when starting selection
    let isDragging = false; // True when dragging fixed selection
    let dragStartX = 0; // X offset when starting to drag
    let dragStartY = 0; // Y offset when starting to drag

    // File input handlers
    // file-input-handler.js handles the button click and file selection display
    // We only need to listen for file changes to load the PDF
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
    }

    if (fileInputDrop) {
        fileInputDrop.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
    }

    async function handleFileSelect(file) {
        try {
            // Cleanup previous PDF if exists
            cleanupPreviousPDF();

            // Show preview section
            pdfPreviewSection.classList.remove('hidden');

            const pdfReady = await ensurePdfJsLoaded();
            if (!pdfReady || typeof window.pdfjsLib === 'undefined') {
                window.showError(
                    'PDF preview engine (PDF.js) is not loaded. Please disable adblock for this site or check that cdnjs/unpkg are not blocked, then refresh the page.',
                    'editorResult'
                );
                pdfPreviewSection.classList.add('hidden');
                cleanupPreviousPDF();
                return;
            }
            if (!window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CANDIDATES[0];
            }

            // Load PDF
            const arrayBuffer = await file.arrayBuffer();
            pdfDoc = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            pageCount = pdfDoc.numPages;

            // Universal page count validation
            const isValid = await window.validatePdfPageLimit(file);
            if (!isValid) {
                // Hide preview sections on validation error
                pdfPreviewSection.classList.add('hidden');
                cleanupPreviousPDF();
                return;
            }

            // Populate page selector
            pageSelector.innerHTML = '';
            const pageLabel = window.PAGE_LABEL || 'Page';
            for (let i = 1; i <= pageCount; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `${pageLabel} ${i}`;
                pageSelector.appendChild(option);
            }

            // Load first page
            currentPage = 1;
            await renderPage(1);

            // Enable edit button
            if (editButton) {
                editButton.disabled = false;
                editButton.classList.remove('opacity-50', 'cursor-not-allowed');
            }

        } catch (error) {
            window.showError(window.FAILED_TO_LOAD_PDF || 'Failed to load PDF file. Please try again.', 'editorResult');
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error loading PDF:', error);
            }
        }
    }

    function cleanupPreviousPDF() {
        // Cleanup previous PDF document
        if (pdfDoc) {
            try {
                pdfDoc.destroy();
            } catch (e) {
                // Ignore cleanup errors
            }
            pdfDoc = null;
        }

        // Reset state
        currentPage = 1;
        pageCount = 0;
        currentSelection = null;
        isSelecting = false;
        isDragging = false;

        // Clear canvas
        if (pdfCanvas) {
            const ctx = pdfCanvas.getContext('2d');
            ctx.clearRect(0, 0, pdfCanvas.width, pdfCanvas.height);
        }
    }

    async function renderPage(pageNum) {
        if (!pdfDoc) return;

        try {
            const page = await pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: 1.0 });

            // Calculate scale to fit canvas in viewport (max width 600px, max height 700px)
            const maxWidth = 600;
            const maxHeight = 700; // Max height to fit in viewport without scrolling
            const widthScale = maxWidth / viewport.width;
            const heightScale = maxHeight / viewport.height;
            scale = Math.min(widthScale, heightScale, 1.0);
            const scaledViewport = page.getViewport({ scale: scale });

            // Set canvas dimensions to match viewport
            canvasWidth = scaledViewport.width;
            canvasHeight = scaledViewport.height;
            pdfCanvas.width = canvasWidth;
            pdfCanvas.height = canvasHeight;

            // Store PDF dimensions in points
            pdfPageWidth = viewport.width;
            pdfPageHeight = viewport.height;

            // Render PDF page
            const renderContext = {
                canvasContext: pdfCanvas.getContext('2d'),
                viewport: scaledViewport
            };

            await page.render(renderContext).promise;

            // Create initial selection covering entire page
            createInitialSelection();

        } catch (error) {
            window.showError('Failed to render PDF page.', 'editorResult');
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error rendering page:', error);
            }
        }
    }

    function createInitialSelection() {
        // Get actual canvas display dimensions
        const rect = pdfCanvas.getBoundingClientRect();
        const displayWidth = rect.width;
        const displayHeight = rect.height;

        // Create selection covering almost entire page with small margins
        // Use 5% margin on each side for better UX
        const marginX = displayWidth * 0.05;
        const marginY = displayHeight * 0.05;

        const initialX = marginX;
        const initialY = marginY;
        const initialWidth = displayWidth - (marginX * 2);
        const initialHeight = displayHeight - (marginY * 2);

        currentSelection = {
            x: initialX,
            y: initialY,
            width: initialWidth,
            height: initialHeight
        };

        updateSelection(initialX, initialY, initialWidth, initialHeight);
        updateOverlay(initialX, initialY, initialWidth, initialHeight);
        updateCropCoordinates();
        // Enable edit button
        if (editButton) {
            editButton.disabled = false;
            editButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }

        // Show ready indicator
        if (cropReadyIndicator) {
            cropReadyIndicator.textContent = window.CROP_AREA_READY || 'Crop area ready! Drag the box to move it, drag from outside to create a new selection, or use handles to resize.';
            cropReadyIndicator.classList.remove('hidden');
        }
    }

    pageSelector.addEventListener('change', async (e) => {
        currentPage = parseInt(e.target.value);
        await renderPage(currentPage);
        // Selection will be recreated automatically in renderPage
    });

    // Pages option handlers
    const pagesAllRadio = document.getElementById('pagesAll');
    const pagesCurrentRadio = document.getElementById('pagesCurrent');
    const pagesCustomRadio = document.getElementById('pagesCustom');
    const pagesCustomInput = document.getElementById('pagesCustomInput');

    if (pagesAllRadio) {
        pagesAllRadio.addEventListener('change', () => {
            if (pagesCustomInput) {
                pagesCustomInput.disabled = true;
                pagesCustomInput.value = '';
            }
        });
    }

    if (pagesCurrentRadio) {
        pagesCurrentRadio.addEventListener('change', () => {
            if (pagesCustomInput) {
                pagesCustomInput.disabled = true;
                pagesCustomInput.value = '';
            }
        });
    }

    if (pagesCustomRadio && pagesCustomInput) {
        pagesCustomRadio.addEventListener('change', () => {
            pagesCustomInput.disabled = false;
            pagesCustomInput.focus();
        });
    }

    // Selection handlers (variables already declared above)

    // Track mouse position for cursor changes
    let mouseX = 0;
    let mouseY = 0;
    let isMouseOverSelection = false;

    // Handle cursor changes when mouse moves over canvas
    pdfCanvas.addEventListener('mousemove', (e) => {
        if (!pdfDoc) return;

        const rect = pdfCanvas.getBoundingClientRect();
        mouseX = e.clientX - rect.left;
        mouseY = e.clientY - rect.top;

        // Only change cursor if not actively selecting or dragging
        if (!isSelecting && !isDragging && currentSelection && currentSelection.width > 0 && currentSelection.height > 0) {
            // Check if mouse is over a handle
            const handles = cropSelection.querySelectorAll('.crop-handle');
            let isOverHandle = false;
            for (const handle of handles) {
                const handleRect = handle.getBoundingClientRect();
                if (e.clientX >= handleRect.left && e.clientX <= handleRect.right &&
                    e.clientY >= handleRect.top && e.clientY <= handleRect.bottom) {
                    isOverHandle = true;
                    break;
                }
            }

            // Check if mouse is inside selection
            const isInside = mouseX >= currentSelection.x &&
                           mouseX <= currentSelection.x + currentSelection.width &&
                           mouseY >= currentSelection.y &&
                           mouseY <= currentSelection.y + currentSelection.height;

            if (isInside && !isOverHandle) {
                if (!isMouseOverSelection) {
                    pdfCanvas.style.cursor = 'move';
                    isMouseOverSelection = true;
                }
            } else {
                if (isMouseOverSelection) {
                    pdfCanvas.style.cursor = 'crosshair';
                    isMouseOverSelection = false;
                }
            }
        }
    });

    // Touch move/end handlers for selection creation and dragging
    // Use passive: true by default and only prevent when actively interacting with PDF area
    document.addEventListener('touchmove', (e) => {
        if (!pdfDoc) return;

        // Only handle if we're actively selecting or dragging
        if (!isSelecting && !isDragging) return;

        const touch = e.touches[0];
        if (!touch) return;

        // Check if touch is within or originated from the PDF canvas container
        const container = pdfCanvasContainer;
        if (!container) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;

        // Mirror logic from mousemove
        if (isDragging && currentSelection) {
            let newX = x - dragStartX;
            let newY = y - dragStartY;

            newX = Math.max(0, Math.min(newX, canvasWidth - currentSelection.width));
            newY = Math.max(0, Math.min(newY, canvasHeight - currentSelection.height));

            currentSelection.x = newX;
            currentSelection.y = newY;

            updateSelection(newX, newY, currentSelection.width, currentSelection.height);
            updateOverlay(newX, newY, currentSelection.width, currentSelection.height);
        } else if (isSelecting) {
            let selX = Math.min(selectionStartX, x);
            let selY = Math.min(selectionStartY, y);
            let selWidth = Math.abs(x - selectionStartX);
            let selHeight = Math.abs(y - selectionStartY);

            currentSelection = {
                x: selX,
                y: selY,
                width: selWidth,
                height: selHeight
            };

            updateSelection(selX, selY, selWidth, selHeight);
            updateOverlay(selX, selY, selWidth, selHeight);
            updateCropCoordinates();
        }

        // Prevent default only during active interaction to avoid blocking page scroll
        e.preventDefault();
    }, { passive: false });

    document.addEventListener('touchend', () => {
        if (isSelecting && !isDragging) {
            isSelecting = false;
            pdfCanvas.style.cursor = 'crosshair';

            if (currentSelection && (currentSelection.width < 10 || currentSelection.height < 10)) {
                createInitialSelection();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = window.SELECTION_TOO_SMALL || 'Selection too small. Full page selected. Drag to create a new selection or drag the box to move it.';
                }
            } else if (currentSelection) {
                updateCropCoordinates();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = window.CROP_AREA_SELECTED || 'Crop area selected! Drag the box to move it or use handles to resize. Click "Crop PDF" when ready.';
                }
            }
        } else if (isDragging) {
            isDragging = false;
            pdfCanvas.style.cursor = isMouseOverSelection ? 'move' : 'crosshair';
            if (currentSelection) {
                updateCropCoordinates();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = window.CROP_AREA_MOVED || 'Crop area moved! Drag again to reposition or use handles to resize. Click "Crop PDF" when ready.';
                }
            }
        }
    });

    // Reset cursor when mouse leaves canvas
    pdfCanvas.addEventListener('mouseleave', () => {
        pdfCanvas.style.cursor = 'crosshair';
        isMouseOverSelection = false;
    });

    // Shared helper to start drag or selection (mouse/touch)
    function startSelectionOrDrag(clientX, clientY, target) {
        if (!pdfDoc) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = clientX - rect.left;
        const y = clientY - rect.top;

        // If starting from cropSelection (but not handle) - drag selection
        if (target === cropSelection) {
            if (!currentSelection || currentSelection.width <= 0 || currentSelection.height <= 0) {
                return;
            }
            isDragging = true;
            dragStartX = x - currentSelection.x;
            dragStartY = y - currentSelection.y;
            pdfCanvas.style.cursor = 'grabbing';
            return;
        }

        // If clicking on handle - let handle logic handle it
        if (target && target.classList && target.classList.contains('crop-handle')) {
            return;
        }

        // Check if clicking inside existing selection - allow moving it
        if (currentSelection && currentSelection.width > 0 && currentSelection.height > 0) {
            const isInside = x >= currentSelection.x &&
                           x <= currentSelection.x + currentSelection.width &&
                           y >= currentSelection.y &&
                           y <= currentSelection.y + currentSelection.height;

            if (isInside) {
                isDragging = true;
                dragStartX = x - currentSelection.x;
                dragStartY = y - currentSelection.y;
                pdfCanvas.style.cursor = 'grabbing';
                return;
            }
        }

        // Start creating new selection (drag-to-select)
        isSelecting = true;
        selectionStartX = x;
        selectionStartY = y;
        pdfCanvas.style.cursor = 'crosshair';

        currentSelection = {
            x: x,
            y: y,
            width: 0,
            height: 0
        };

        cropSelection.classList.remove('hidden');
        updateSelection(x, y, 0, 0);

        if (cropReadyIndicator) {
            cropReadyIndicator.textContent = window.DRAG_TO_SELECT || 'Drag to select crop area...';
            cropReadyIndicator.classList.remove('hidden');
        }
    }

    // Add mousedown handler to cropSelection element for dragging
    if (cropSelection) {
        cropSelection.addEventListener('mousedown', (e) => {
            startSelectionOrDrag(e.clientX, e.clientY, cropSelection);
            e.preventDefault();
            e.stopPropagation();
        });

        // Touch support for dragging selection
        cropSelection.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            if (!touch) return;

            // Only prevent default if we're actually starting a drag operation
            const rect = cropSelection.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;

            // Check if touch is within selection area
            if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
                startSelectionOrDrag(touch.clientX, touch.clientY, cropSelection);
                e.preventDefault();
                e.stopPropagation();
            }
        }, { passive: false });
    }

    pdfCanvas.addEventListener('mousedown', (e) => {
        startSelectionOrDrag(e.clientX, e.clientY, e.target);
        e.preventDefault();
    });

    // Touch support for creating/dragging selection on canvas
    pdfCanvas.addEventListener('touchstart', (e) => {
        const touch = e.touches[0];
        if (!touch) return;

        // Only prevent default if touch is within canvas bounds and we're starting selection
        const rect = pdfCanvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;

        // Check if touch is within canvas area
        if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
            startSelectionOrDrag(touch.clientX, touch.clientY, e.target);
            e.preventDefault();
        }
    }, { passive: false });

    // Handle mousemove for selection creation and dragging
    // (mousemove for cursor changes is handled above)
    document.addEventListener('mousemove', (e) => {
        if (!pdfDoc) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // If dragging existing selection - handle this first
        if (isDragging && currentSelection) {
            let newX = x - dragStartX;
            let newY = y - dragStartY;

            // Get actual canvas display dimensions
            const rect = pdfCanvas.getBoundingClientRect();
            const displayWidth = rect.width;
            const displayHeight = rect.height;

            // Constrain to canvas display bounds
            newX = Math.max(0, Math.min(newX, displayWidth - currentSelection.width));
            newY = Math.max(0, Math.min(newY, displayHeight - currentSelection.height));

            // Update currentSelection immediately for dragging
            currentSelection.x = newX;
            currentSelection.y = newY;

            updateSelection(newX, newY, currentSelection.width, currentSelection.height);
            updateOverlay(newX, newY, currentSelection.width, currentSelection.height);

            // Update coordinates in real-time
            updateCropCoordinates();
            return;
        }

        // If creating new selection (drag-to-select)
        if (isSelecting && !isDragging) {
            const minX = Math.min(selectionStartX, x);
            const maxX = Math.max(selectionStartX, x);
            const minY = Math.min(selectionStartY, y);
            const maxY = Math.max(selectionStartY, y);

            const width = maxX - minX;
            const height = maxY - minY;

            // Get actual canvas display dimensions
            const rect = pdfCanvas.getBoundingClientRect();
            const displayWidth = rect.width;
            const displayHeight = rect.height;

            // Constrain to canvas display bounds
            const selX = Math.max(0, Math.min(minX, displayWidth - width));
            const selY = Math.max(0, Math.min(minY, displayHeight - height));
            const selWidth = Math.min(width, displayWidth - selX);
            const selHeight = Math.min(height, displayHeight - selY);

            currentSelection = {
                x: selX,
                y: selY,
                width: selWidth,
                height: selHeight
            };

            updateSelection(selX, selY, selWidth, selHeight);
            updateOverlay(selX, selY, selWidth, selHeight);
            updateCropCoordinates();
        }
    });

    document.addEventListener('mouseup', (e) => {
        if (isSelecting && !isDragging) {
            // Finish creating selection
            isSelecting = false;
            pdfCanvas.style.cursor = 'crosshair';

            // Ensure minimum size
            if (currentSelection && (currentSelection.width < 10 || currentSelection.height < 10)) {
                // Too small - restore to full page or previous selection
                createInitialSelection();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = window.SELECTION_TOO_SMALL || 'Selection too small. Full page selected. Drag to create a new selection or drag the box to move it.';
                }
            } else if (currentSelection) {
                // Valid selection - update coordinates and show ready message
                updateCropCoordinates();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = window.CROP_AREA_SELECTED || 'Crop area selected! Drag the box to move it or use handles to resize. Click "Crop PDF" when ready.';
                }
            }
        } else if (isDragging) {
            isDragging = false;
            pdfCanvas.style.cursor = isMouseOverSelection ? 'move' : 'crosshair';
            // Update coordinates after dragging
            if (currentSelection) {
                updateCropCoordinates();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = window.CROP_AREA_MOVED || 'Crop area moved! Drag again to reposition or use handles to resize. Click "Crop PDF" when ready.';
                }
            }
        }
    });

    function updateSelection(x, y, width, height) {
        // Get actual canvas display dimensions
        const rect = pdfCanvas.getBoundingClientRect();
        const displayWidth = rect.width;
        const displayHeight = rect.height;

        // Ensure selection is within canvas display bounds
        x = Math.max(0, Math.min(x, displayWidth));
        y = Math.max(0, Math.min(y, displayHeight));

        if (width < 0) {
            x += width;
            width = Math.abs(width);
        }
        if (height < 0) {
            y += height;
            height = Math.abs(height);
        }

        width = Math.min(width, displayWidth - x);
        height = Math.min(height, displayHeight - y);

        cropSelection.style.left = `${x}px`;
        cropSelection.style.top = `${y}px`;
        cropSelection.style.width = `${width}px`;
        cropSelection.style.height = `${height}px`;

        // Ensure crop selection is visible
        cropSelection.classList.remove('hidden');

        // Update overlay to darken outside selection
        updateOverlay(x, y, width, height);
    }

    function updateOverlay(x, y, width, height) {
        // Make overlay optional - can be hidden if too distracting
        // For now, keep it very subtle
        if (!cropOverlay || cropSelection.classList.contains('hidden') || !currentSelection) {
            if (cropOverlay) {
                cropOverlay.classList.add('hidden');
            }
            return;
        }

        // Show overlay but make it very subtle
        cropOverlay.classList.remove('hidden');

        // Top overlay
        cropOverlayTop.style.left = '0px';
        cropOverlayTop.style.top = '0px';
        cropOverlayTop.style.width = `${canvasWidth}px`;
        cropOverlayTop.style.height = `${y}px`;

        // Right overlay
        cropOverlayRight.style.left = `${x + width}px`;
        cropOverlayRight.style.top = `${y}px`;
        cropOverlayRight.style.width = `${canvasWidth - x - width}px`;
        cropOverlayRight.style.height = `${height}px`;

        // Bottom overlay
        cropOverlayBottom.style.left = '0px';
        cropOverlayBottom.style.top = `${y + height}px`;
        cropOverlayBottom.style.width = `${canvasWidth}px`;
        cropOverlayBottom.style.height = `${canvasHeight - y - height}px`;

        // Left overlay
        cropOverlayLeft.style.left = '0px';
        cropOverlayLeft.style.top = `${y}px`;
        cropOverlayLeft.style.width = `${x}px`;
        cropOverlayLeft.style.height = `${height}px`;
    }

    function resetSelection() {
        cropSelection.classList.add('hidden');
        if (cropOverlay) {
            cropOverlay.classList.add('hidden');
        }
        currentSelection = null;
        isDragging = false;
        document.getElementById('x').value = '0';
        document.getElementById('y').value = '0';
        document.getElementById('width').value = '';
        document.getElementById('height').value = '';
    }

    function updateCropCoordinates() {
        if (!currentSelection) {
            // Disable button if no selection
            if (editButton) {
                editButton.disabled = true;
                editButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
            return;
        }

        // Convert canvas coordinates to PDF points
        // PDF coordinate system: (0,0) is bottom-left
        // Canvas coordinate system: (0,0) is top-left

        // Use proper scale factors for X and Y to maintain aspect ratio
        const scaleX = pdfPageWidth / canvasWidth;
        const scaleY = pdfPageHeight / canvasHeight;

        // X coordinate (left edge) in points
        const x = currentSelection.x * scaleX;

        // Y coordinate (bottom edge) in points
        // Need to flip Y because PDF uses bottom-left origin
        const y = (canvasHeight - currentSelection.y - currentSelection.height) * scaleY;

        // Width and height in points
        const width = currentSelection.width * scaleX;
        const height = currentSelection.height * scaleY;

        // Update form fields
        const xInput = document.getElementById('x');
        const yInput = document.getElementById('y');
        const widthInput = document.getElementById('width');
        const heightInput = document.getElementById('height');

        if (xInput) xInput.value = x.toFixed(2);
        if (yInput) yInput.value = y.toFixed(2);
        if (widthInput) widthInput.value = width.toFixed(2);
        if (heightInput) heightInput.value = height.toFixed(2);

        // Enable button if coordinates are valid
        if (editButton && widthInput && widthInput.value && parseFloat(widthInput.value) > 0) {
            editButton.disabled = false;
            editButton.classList.remove('opacity-50', 'cursor-not-allowed');
        } else if (editButton) {
            editButton.disabled = true;
            editButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    // Handle resize handles
    const handles = cropSelection.querySelectorAll('.crop-handle');
    let resizeHandle = null;
    let resizeStartX = 0;
    let resizeStartY = 0;
    let resizeStartSelection = null;

    handles.forEach(handle => {
        handle.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            if (!currentSelection) return;

            resizeHandle = handle;
            const rect = pdfCanvas.getBoundingClientRect();
            resizeStartX = e.clientX - rect.left;
            resizeStartY = e.clientY - rect.top;
            resizeStartSelection = { ...currentSelection };
        });

        // Touch support for resize handles
        handle.addEventListener('touchstart', (e) => {
            e.stopPropagation();
            const touch = e.touches[0];
            if (!touch || !currentSelection) return;

            resizeHandle = handle;
            const rect = pdfCanvas.getBoundingClientRect();
            resizeStartX = touch.clientX - rect.left;
            resizeStartY = touch.clientY - rect.top;
            resizeStartSelection = { ...currentSelection };
            e.preventDefault();
        }, { passive: false });
    });

    document.addEventListener('mousemove', (e) => {
        if (!resizeHandle || !resizeStartSelection) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const deltaX = x - resizeStartX;
        const deltaY = y - resizeStartY;

        let newX = resizeStartSelection.x;
        let newY = resizeStartSelection.y;
        let newWidth = resizeStartSelection.width;
        let newHeight = resizeStartSelection.height;

        const handleClass = resizeHandle.className.split(' ').find(c => c !== 'crop-handle');

        if (handleClass === 'nw') {
            newX = Math.max(0, resizeStartSelection.x + deltaX);
            newY = Math.max(0, resizeStartSelection.y + deltaY);
            newWidth = resizeStartSelection.width - deltaX;
            newHeight = resizeStartSelection.height - deltaY;
        } else if (handleClass === 'ne') {
            newY = Math.max(0, resizeStartSelection.y + deltaY);
            newWidth = resizeStartSelection.width + deltaX;
            newHeight = resizeStartSelection.height - deltaY;
        } else if (handleClass === 'sw') {
            newX = Math.max(0, resizeStartSelection.x + deltaX);
            newWidth = resizeStartSelection.width - deltaX;
            newHeight = resizeStartSelection.height + deltaY;
        } else if (handleClass === 'se') {
            newWidth = resizeStartSelection.width + deltaX;
            newHeight = resizeStartSelection.height + deltaY;
        } else if (handleClass === 'n') {
            newY = Math.max(0, resizeStartSelection.y + deltaY);
            newHeight = resizeStartSelection.height - deltaY;
        } else if (handleClass === 's') {
            newHeight = resizeStartSelection.height + deltaY;
        } else if (handleClass === 'w') {
            newX = Math.max(0, resizeStartSelection.x + deltaX);
            newWidth = resizeStartSelection.width - deltaX;
        } else if (handleClass === 'e') {
            newWidth = resizeStartSelection.width + deltaX;
        }

        // Constrain to canvas bounds
        newX = Math.max(0, Math.min(newX, canvasWidth));
        newY = Math.max(0, Math.min(newY, canvasHeight));
        newWidth = Math.max(10, Math.min(newWidth, canvasWidth - newX));
        newHeight = Math.max(10, Math.min(newHeight, canvasHeight - newY));

        // Update currentSelection immediately during resize
        currentSelection = {
            x: newX,
            y: newY,
            width: newWidth,
            height: newHeight
        };

        updateSelection(newX, newY, newWidth, newHeight);
        updateOverlay(newX, newY, newWidth, newHeight);

        // Update coordinates in real-time during resize
        updateCropCoordinates();
    });

    document.addEventListener('mouseup', (e) => {
        if (resizeHandle) {
            // Update coordinates after resize
            if (currentSelection) {
                // Ensure selection is valid
                if (currentSelection.width > 0 && currentSelection.height > 0) {
                    updateCropCoordinates();
                }
            }
            resizeHandle = null;
            resizeStartSelection = null;
        }
    });

    // Touch move handler for resize handles
    // Only prevents default when actively resizing a handle
    document.addEventListener('touchmove', (e) => {
        // Only handle when actively resizing
        if (!resizeHandle || !resizeStartSelection) return;

        const touch = e.touches[0];
        if (!touch) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        const deltaX = x - resizeStartX;
        const deltaY = y - resizeStartY;

        let newX = resizeStartSelection.x;
        let newY = resizeStartSelection.y;
        let newWidth = resizeStartSelection.width;
        let newHeight = resizeStartSelection.height;

        const handleClass = resizeHandle.className.split(' ').find(c => c !== 'crop-handle');

        if (handleClass === 'nw') {
            newX = Math.max(0, resizeStartSelection.x + deltaX);
            newY = Math.max(0, resizeStartSelection.y + deltaY);
            newWidth = resizeStartSelection.width - deltaX;
            newHeight = resizeStartSelection.height - deltaY;
        } else if (handleClass === 'ne') {
            newY = Math.max(0, resizeStartSelection.y + deltaY);
            newWidth = resizeStartSelection.width + deltaX;
            newHeight = resizeStartSelection.height - deltaY;
        } else if (handleClass === 'sw') {
            newX = Math.max(0, resizeStartSelection.x + deltaX);
            newWidth = resizeStartSelection.width - deltaX;
            newHeight = resizeStartSelection.height + deltaY;
        } else if (handleClass === 'se') {
            newWidth = resizeStartSelection.width + deltaX;
            newHeight = resizeStartSelection.height + deltaY;
        } else if (handleClass === 'n') {
            newY = Math.max(0, resizeStartSelection.y + deltaY);
            newHeight = resizeStartSelection.height - deltaY;
        } else if (handleClass === 's') {
            newHeight = resizeStartSelection.height + deltaY;
        } else if (handleClass === 'w') {
            newX = Math.max(0, resizeStartSelection.x + deltaX);
            newWidth = resizeStartSelection.width - deltaX;
        } else if (handleClass === 'e') {
            newWidth = resizeStartSelection.width + deltaX;
        }

        // Constrain to canvas bounds
        newX = Math.max(0, Math.min(newX, canvasWidth));
        newY = Math.max(0, Math.min(newY, canvasHeight));
        newWidth = Math.max(10, Math.min(newWidth, canvasWidth - newX));
        newHeight = Math.max(10, Math.min(newHeight, canvasHeight - newY));

        // Update currentSelection immediately during resize
        currentSelection = {
            x: newX,
            y: newY,
            width: newWidth,
            height: newHeight
        };

        updateSelection(newX, newY, newWidth, newHeight);
        updateOverlay(newX, newY, newWidth, newHeight);

        // Update coordinates in real-time during resize
        updateCropCoordinates();

        // Prevent default only during active resize
        e.preventDefault();
    }, { passive: false });

    // Touch end handler for resize
    document.addEventListener('touchend', (e) => {
        if (resizeHandle) {
            // Update coordinates after resize
            if (currentSelection) {
                // Ensure selection is valid
                if (currentSelection.width > 0 && currentSelection.height > 0) {
                    updateCropCoordinates();
                }
            }
            resizeHandle = null;
            resizeStartSelection = null;
        }
    });

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!currentSelection || !document.getElementById('width').value) {
            window.showError('Please select the crop area by dragging on the PDF. The blue highlighted area will be kept.', 'editorResult');
            return;
        }

        const formData = new FormData();
        const singleFieldName = window.FILE_INPUT_NAME || 'pdf_file';

        const selectedFiles = (fileInput?.files && fileInput.files.length > 0)
            ? fileInput.files
            : (fileInputDrop?.files && fileInputDrop.files.length > 0)
                ? fileInputDrop.files
                : null;

        const isBatchMode = Boolean(
            window.BATCH_ENABLED &&
            window.IS_PREMIUM &&
            selectedFiles &&
            selectedFiles.length > 1 &&
            window.BATCH_API_URL &&
            window.BATCH_FIELD_NAME
        );

        const selectedFile = selectedFiles?.[0] || null;
        if (!selectedFile) {
            window.showError(window.SELECT_FILE_MESSAGE || 'Please select a file', 'editorResult');
            return;
        }

        if (isBatchMode) {
            const batchFieldName = window.BATCH_FIELD_NAME;
            Array.from(selectedFiles).forEach((f) => {
                formData.append(batchFieldName, f);
            });
        } else {
            formData.append(singleFieldName, selectedFile);
        }
        const xValue = document.getElementById('x').value;
        const yValue = document.getElementById('y').value;
        const widthValue = document.getElementById('width').value;
        const heightValue = document.getElementById('height').value;

        // Ensure values are valid numbers
        if (!xValue || !yValue || !widthValue || !heightValue) {
            window.showError('Please adjust the crop area first.', 'editorResult');
            return;
        }

        formData.append('x', parseFloat(xValue).toFixed(2));
        formData.append('y', parseFloat(yValue).toFixed(2));
        formData.append('width', parseFloat(widthValue).toFixed(2));
        formData.append('height', parseFloat(heightValue).toFixed(2));

        // Get pages value from radio buttons
        const pagesAllRadio = document.getElementById('pagesAll');
        const pagesCurrentRadio = document.getElementById('pagesCurrent');
        const pagesCustomRadio = document.getElementById('pagesCustom');
        const pagesCustomInput = document.getElementById('pagesCustomInput');

        let pagesValue = 'all';
        if (pagesCurrentRadio && pagesCurrentRadio.checked) {
            // Current page only
            pagesValue = currentPage.toString();
        } else if (pagesCustomRadio && pagesCustomRadio.checked && pagesCustomInput && pagesCustomInput.value.trim()) {
            // Custom pages
            pagesValue = pagesCustomInput.value.trim();
        } else {
            // All pages (default) - explicitly send 'all' to ensure backend processes all pages
            pagesValue = 'all';
        }

        formData.append('pages', pagesValue);

        // Add scale to page size option
        const scaleToPageSizeCheckbox = document.getElementById('scaleToPageSize');
        if (scaleToPageSizeCheckbox && scaleToPageSizeCheckbox.checked) {
            formData.append('scale_to_page_size', 'true');
        } else {
            formData.append('scale_to_page_size', 'false');
        }

        // Hide previous results
        hideResult();
        hideDownload();

        // Show loading (disable progress bar for batch mode)
        window.showLoading('loadingContainer', { showProgress: !isBatchMode });

        // Disable form
        setFormDisabled(true);

        try {
            const apiUrl = isBatchMode ? window.BATCH_API_URL : window.API_URL;
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN
                },
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));

                // Always use API error if available
                if (errorData.error) {
                    throw new Error(errorData.error);
                } else {
                    throw new Error('API returned error but no error message');
                }
            }

            const blob = await response.blob();

            // Success
            window.hideLoading('loadingContainer');
            const contentDisposition = response.headers.get('content-disposition');
            let downloadName = isBatchMode ? 'convertica.zip' : selectedFile.name;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    downloadName = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            window.showDownloadButton(blob, downloadName, 'downloadContainer', {
                successTitle: window.SUCCESS_TITLE || 'Editing Complete!',
                downloadButtonText: window.DOWNLOAD_BUTTON_TEXT || 'Download File',
                convertAnotherText: window.EDIT_ANOTHER_TEXT || 'Edit another file',
                onConvertAnother: () => {
                    const selectedFileDiv = document.getElementById('selectedFile');
                    if (selectedFileDiv) {
                        selectedFileDiv.classList.add('hidden');
                    }
                    const fileInput = document.getElementById('fileInput');
                    if (fileInput) {
                        fileInput.value = '';
                    }
                    const fileInputDrop = document.getElementById('fileInputDrop');
                    if (fileInputDrop) {
                        fileInputDrop.value = '';
                    }
                    hideDownload();
                    cleanupPreviousPDF();
                    if (pdfPreviewSection) {
                        pdfPreviewSection.classList.add('hidden');
                    }
                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });
                    setTimeout(() => {
                        const selectFileButton = document.getElementById('selectFileButton');
                        if (selectFileButton) {
                            selectFileButton.focus({ preventScroll: true });
                        }
                    }, 800);
                }
            });
            setFormDisabled(false);

        } catch (error) {
            window.hideLoading('loadingContainer');
            window.showError(error.message || window.ERROR_MESSAGE, 'editorResult');
            setFormDisabled(false);
        }
    });

    function hideDownload() {
        window.hideDownload('downloadContainer');
    }

    function hideResult() {
        if (resultContainer) {
            resultContainer.classList.add('hidden');
        }
    }

    function setFormDisabled(disabled) {
        if (editButton) {
            editButton.disabled = disabled;
        }
        const inputs = form.querySelectorAll('input, select, textarea, button');
        inputs.forEach(input => {
            if (input !== editButton) {
                input.disabled = disabled;
            }
        });
    }
});
