/**
 * PDF Watermark Editor Component
 * Visual PDF watermark positioning with color and opacity controls
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
    const watermarkSettingsSection = document.getElementById('watermarkSettingsSection');
    const pdfCanvas = document.getElementById('pdfCanvas');
    const pdfCanvasContainer = document.getElementById('pdfCanvasContainer');
    const watermarkPreview = document.getElementById('watermarkPreview');
    const pageSelector = document.getElementById('pageSelector');
    const editButton = document.getElementById('editButton');
    const resultContainer = document.getElementById('editorResult');

    // Watermark controls
    const watermarkTypeText = document.getElementById('watermarkTypeText');
    const watermarkTypeImage = document.getElementById('watermarkTypeImage');
    const textWatermarkSection = document.getElementById('textWatermarkSection');
    const imageWatermarkSection = document.getElementById('imageWatermarkSection');
    const fontSizeSection = document.getElementById('fontSizeSection');
    const watermarkText = document.getElementById('watermark_text');
    const watermarkFile = document.getElementById('watermark_file');
    const watermarkFileButton = document.getElementById('watermarkFileButton');
    const watermarkFileName = document.getElementById('watermarkFileName');
    const watermarkColor = document.getElementById('watermark_color');
    const watermarkColorText = document.getElementById('watermark_color_text');
    const opacitySlider = document.getElementById('opacity');
    const opacityValue = document.getElementById('opacityValue');
    const fontSizeSlider = document.getElementById('font_size');
    const fontSizeValue = document.getElementById('fontSizeValue');
    const pagesInput = document.getElementById('pages');
    const positionInput = document.getElementById('position');
    const xInput = document.getElementById('x');
    const yInput = document.getElementById('y');
    const rotationInput = document.getElementById('rotation');
    const scaleInput = document.getElementById('scale');

    // State
    let pdfDoc = null;
    let currentPage = 1;
    let pageCount = 0;
    let scale = 1.0;
    let pdfPageWidth = 0;
    let pdfPageHeight = 0;
    let canvasWidth = 0;
    let canvasHeight = 0;
    let watermarkX = null;
    let watermarkY = null;
    let watermarkImage = null;
    let watermarkRotation = 0.0;
    let watermarkScale = 1.0;
    let currentRenderTask = null;

    // Position sliders (now used on all screen sizes)
    const watermarkXSlider = document.getElementById('watermarkXSlider');
    const watermarkYSlider = document.getElementById('watermarkYSlider');

    function clamp01(v) {
        return Math.max(0, Math.min(1, v));
    }

    function percentToRatio(value) {
        const n = Number(value);
        if (!Number.isFinite(n)) return 0.5;
        return clamp01(n / 100);
    }

    function setSlidersFromRatio(xRatio, yRatio) {
        if (watermarkXSlider) watermarkXSlider.value = String(Math.round(clamp01(xRatio) * 100));
        if (watermarkYSlider) watermarkYSlider.value = String(Math.round(clamp01(yRatio) * 100));
    }

    function applyPositionFromSliders() {
        if (!pdfDoc || !pdfPageWidth || !pdfPageHeight) {
            return;
        }
        if (!watermarkXSlider || !watermarkYSlider) {
            return;
        }

        const xRatio = percentToRatio(watermarkXSlider.value);
        const yRatio = percentToRatio(watermarkYSlider.value);

        // X in PDF points from left
        watermarkX = pdfPageWidth * xRatio;
        // Y slider: 0 = bottom, 100 = top
        watermarkY = pdfPageHeight * yRatio;

        if (xInput) xInput.value = watermarkX.toFixed(2);
        if (yInput) yInput.value = watermarkY.toFixed(2);
        if (positionInput) positionInput.value = 'custom';

        updateWatermarkPreview();
    }

    function bindSliderPositionHandlers() {
        if (watermarkXSlider) {
            watermarkXSlider.addEventListener('input', () => {
                applyPositionFromSliders();
            });
        }
        if (watermarkYSlider) {
            watermarkYSlider.addEventListener('input', () => {
                applyPositionFromSliders();
            });
        }
    }

    // Enable slider-driven positioning
    bindSliderPositionHandlers();

    // Watermark interaction states
    let isDraggingWatermark = false;
    let isScaling = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let currentScaleCorner = null;
    let isInteracting = false; // Track if user is actively interacting
    let isPinching = false; // Track pinch gesture for mobile
    let initialPinchDistance = 0;

    // Visual enhancement elements
    let alignmentGrid = null;
    let isShowingGrid = false;
    let initialScale = 1.0;
    let initialDistance = 0;

    // Watermark type toggle
    if (watermarkTypeText && watermarkTypeImage) {
        watermarkTypeText.addEventListener('change', () => {
            if (watermarkTypeText.checked) {
                textWatermarkSection.classList.remove('hidden');
                imageWatermarkSection.classList.add('hidden');
                fontSizeSection.classList.remove('hidden');
                // Clear file input when switching to text
                if (watermarkFile) {
                    watermarkFile.value = '';
                }
                if (watermarkFileName) {
                    watermarkFileName.textContent = '';
                }
                updateWatermarkPreview();
            }
        });

        watermarkTypeImage.addEventListener('change', () => {
            if (watermarkTypeImage.checked) {
                textWatermarkSection.classList.add('hidden');
                imageWatermarkSection.classList.remove('hidden');
                fontSizeSection.classList.add('hidden');
                updateWatermarkPreview();
            }
        });
    }

    // Watermark controls real-time updates
    const updateWatermarkFromControls = () => {
        if (pdfDoc && watermarkX !== null && watermarkY !== null) {
            updateWatermarkPreview();
        }
    };

    // Color inputs
    if (watermarkColor) {
        watermarkColor.addEventListener('input', updateWatermarkFromControls);
    }
    if (watermarkColorText) {
        watermarkColorText.addEventListener('input', updateWatermarkFromControls);
    }

    // Opacity slider
    if (opacitySlider) {
        opacitySlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            if (opacityValue) opacityValue.textContent = value + '%';
            updateWatermarkFromControls();
        });
    }

    // Font size slider
    if (fontSizeSlider) {
        fontSizeSlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            if (fontSizeValue) fontSizeValue.textContent = value + 'px';
            updateWatermarkFromControls();
        });
    }

    // Rotation slider
    const rotationSlider = document.getElementById('rotation_slider');
    const rotationValueDisplay = document.getElementById('rotationValue');

    if (rotationSlider) {
        rotationSlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            if (rotationValueDisplay) rotationValueDisplay.textContent = value + '°';

            // Update watermark rotation (convert to 0-360 range for internal use)
            watermarkRotation = value < 0 ? 360 + value : value;

            // Update hidden input
            if (rotationInput) rotationInput.value = watermarkRotation.toFixed(1);

            updateWatermarkFromControls();
        });
    }

    // Scale slider
    const scaleSlider = document.getElementById('scale_slider');
    const scaleValueDisplay = document.getElementById('scaleValue');

    if (scaleSlider) {
        scaleSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            if (scaleValueDisplay) scaleValueDisplay.textContent = Math.round(value * 100) + '%';

            // Calculate max scale based on page size
            let maxScale = 3.0;
            const isText = watermarkTypeText?.checked;
            if (pdfDoc && pdfPageWidth && pdfPageHeight) {
                if (isText) {
                    const fontSize = parseInt(fontSizeSlider?.value || 72);
                    const text = watermarkText?.value || 'CONFIDENTIAL';
                    const estimatedWidth = fontSize * text.length * 0.6;
                    const estimatedHeight = fontSize * 1.2;
                    const maxScaleWidth = (pdfPageWidth * 0.95) / estimatedWidth;
                    const maxScaleHeight = (pdfPageHeight * 0.95) / estimatedHeight;
                    maxScale = Math.max(0.5, Math.min(maxScaleWidth, maxScaleHeight, 5.0));
                } else if (watermarkImage) {
                    const baseScale = Math.min(pdfPageWidth / watermarkImage.width, pdfPageHeight / watermarkImage.height) * 0.5;
                    const scaledWidth = watermarkImage.width * baseScale;
                    const scaledHeight = watermarkImage.height * baseScale;
                    const maxScaleWidth = (pdfPageWidth * 0.95) / scaledWidth;
                    const maxScaleHeight = (pdfPageHeight * 0.95) / scaledHeight;
                    maxScale = Math.max(0.5, Math.min(maxScaleWidth, maxScaleHeight, 5.0));
                }
            }

            // Update watermark scale with bounds
            watermarkScale = Math.max(0.1, Math.min(maxScale, value));

            // Update slider if clamped
            if (watermarkScale !== value) {
                scaleSlider.value = watermarkScale;
                if (scaleValueDisplay) scaleValueDisplay.textContent = Math.round(watermarkScale * 100) + '%';
            }

            // Update hidden input
            if (scaleInput) scaleInput.value = watermarkScale.toFixed(2);

            updateWatermarkFromControls();
        });
    }

    // Watermark text
    if (watermarkText) {
        watermarkText.addEventListener('input', updateWatermarkFromControls);
        watermarkText.addEventListener('blur', updateWatermarkFromControls);
    }

    // Watermark file button - trigger file input click
    if (watermarkFileButton && watermarkFile) {
        watermarkFileButton.addEventListener('click', (e) => {
            e.preventDefault();
            watermarkFile.click();
        });
    }

    // Watermark image change
    if (watermarkFile) {
        watermarkFile.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                // Show file name
                if (watermarkFileName) {
                    watermarkFileName.textContent = file.name;
                }
                // Load image for preview
                const reader = new FileReader();
                reader.onload = (event) => {
                    watermarkImage = new Image();
                    watermarkImage.onload = () => {
                        updateWatermarkPreview();
                    };
                    watermarkImage.src = event.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // File input handlers
    // Note: file-input-handler.js handles the button click and file selection display
    // We listen to the 'fileSelected' custom event to load the PDF for preview
    document.addEventListener('fileSelected', (e) => {
        const file = e.detail?.file;
        if (file && file.type === 'application/pdf') {
            handleFileSelect(file);
        }
    });

    // Also listen to direct change events as fallback (in case file-input-handler.js is not loaded)
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            // Small delay for mobile devices
            await new Promise(resolve => setTimeout(resolve, 100));

            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                if (file.type === 'application/pdf') {
                    handleFileSelect(file);
                }
            }
        });
    }

    if (fileInputDrop) {
        fileInputDrop.addEventListener('change', async (e) => {
            // Small delay for mobile devices
            await new Promise(resolve => setTimeout(resolve, 100));

            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                if (file.type === 'application/pdf') {
                    handleFileSelect(file);
                }
            }
        });
    }

    async function handleFileSelect(file) {
        try {
            // Clear any previous errors when selecting a new file
            clearError();

            cleanupPreviousPDF();

            // Show preview section
            pdfPreviewSection.classList.remove('hidden');
            watermarkSettingsSection.classList.remove('hidden');

            // Validate file type
            if (!file || !file.type || !file.type.includes('pdf')) {
                window.showError('Please select a valid PDF file.', 'editorResult');
                // Hide preview sections on validation error
                pdfPreviewSection.classList.add('hidden');
                watermarkSettingsSection.classList.add('hidden');
                return;
            }

            const pdfReady = await ensurePdfJsLoaded();
            if (!pdfReady || typeof window.pdfjsLib === 'undefined') {
                window.showError(
                    'PDF preview engine (PDF.js) is not loaded. Please disable adblock for this site or check that cdnjs/unpkg are not blocked, then refresh the page.',
                    'editorResult'
                );
                pdfPreviewSection.classList.add('hidden');
                watermarkSettingsSection.classList.add('hidden');
                cleanupPreviousPDF();
                return;
            }
            if (!window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CANDIDATES[0];
            }

            // Small delay to ensure file is ready
            await new Promise(resolve => setTimeout(resolve, 50));

            // Load PDF
            const arrayBuffer = await file.arrayBuffer();

            // Check if arrayBuffer is valid
            if (!arrayBuffer || arrayBuffer.byteLength === 0) {
                window.showError('Failed to read file. Please try again.', 'editorResult');
                // Hide preview sections on validation error
                pdfPreviewSection.classList.add('hidden');
                watermarkSettingsSection.classList.add('hidden');
                return;
            }

            // Try loading PDF with retries
            let retryCount = 0;
            const maxRetries = 3;
            while (retryCount < maxRetries) {
                try {
                    pdfDoc = await window.pdfjsLib.getDocument({
                        data: arrayBuffer,
                        verbosity: 0 // Suppress warnings
                    }).promise;

                    if (!pdfDoc) {
                        throw new Error('PDF document is null');
                    }

                    break; // Success, exit retry loop

                } catch (error) {
                    retryCount++;
                    console.error(`PDF load attempt ${retryCount} failed:`, error);

                    if (retryCount >= maxRetries) {
                        window.window.showError('Failed to load PDF file. Please try again.', 'editorResult');
                        // Hide preview sections on load error
                        pdfPreviewSection.classList.add('hidden');
                        watermarkSettingsSection.classList.add('hidden');
                        cleanupPreviousPDF();
                        return;
                    }
                }
            }

            // Get page count
            pageCount = pdfDoc.numPages;

            // Universal page count validation
            const isValid = await window.validatePdfPageLimit(file);
            if (!isValid) {
                // Hide preview sections on validation error
                pdfPreviewSection.classList.add('hidden');
                watermarkSettingsSection.classList.add('hidden');
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
            // More detailed error handling
            let errorMessage = 'Failed to load PDF file. Please try again.';

            if (error && error.message) {
                if (error.message.includes('Invalid PDF')) {
                    errorMessage = 'Invalid PDF file. Please select a valid PDF file.';
                } else if (error.message.includes('password')) {
                    errorMessage = 'This PDF is password protected. Please unlock it first.';
                } else if (error.message.includes('network') || error.message.includes('fetch')) {
                    errorMessage = 'Network error. Please check your connection and try again.';
                } else {
                    errorMessage = `Error: ${error.message}`;
                }
            }

            window.window.showError(errorMessage, 'editorResult');
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error loading PDF:', error);
                console.error('Error details:', {
                    name: error?.name,
                    message: error?.message,
                    stack: error?.stack
                });
            }

            // Hide preview sections on error
            if (pdfPreviewSection) {
                pdfPreviewSection.classList.add('hidden');
            }
            if (watermarkSettingsSection) {
                watermarkSettingsSection.classList.add('hidden');
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
        watermarkX = null;
        watermarkY = null;
        watermarkImage = null;
        isDraggingWatermark = false;
        isScaling = false;

        // Clear canvas
        if (pdfCanvas) {
            const ctx = pdfCanvas.getContext('2d');
            ctx.clearRect(0, 0, pdfCanvas.width, pdfCanvas.height);
        }

        // Clear watermark preview (it's a div, not a canvas)
        if (watermarkPreview) {
            watermarkPreview.innerHTML = '';
            watermarkPreview.classList.add('hidden');
        }
    }

    async function renderPage(pageNum) {
        if (!pdfDoc) return;

        try {
            const page = await pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: 1.0 });

            // Calculate scale to fit canvas in viewport (max width 600px, max height 700px)
            // Account for container padding (p-4 = 16px each side = 32px total)
            // And some margin for watermark controls
            const maxWidth = 600;
            const maxHeight = 700; // Max height to fit in viewport without scrolling
            const widthScale = maxWidth / viewport.width;
            const heightScale = maxHeight / viewport.height;
            scale = Math.min(widthScale, heightScale, 1.0);
            const scaledViewport = page.getViewport({ scale: scale });

            // Set canvas dimensions
            canvasWidth = scaledViewport.width;
            canvasHeight = scaledViewport.height;
            pdfCanvas.width = canvasWidth;
            pdfCanvas.height = canvasHeight;

            // Reset any CSS scaling to ensure accurate coordinate calculations
            pdfCanvas.style.width = '';
            pdfCanvas.style.height = '';

            // Store PDF dimensions in points
            pdfPageWidth = viewport.width;
            pdfPageHeight = viewport.height;

            // Cancel previous render if exists
            if (currentRenderTask) {
                currentRenderTask.cancel();
                currentRenderTask = null;
            }

            // Render PDF page
            const renderContext = {
                canvasContext: pdfCanvas.getContext('2d'),
                viewport: scaledViewport
            };

            currentRenderTask = page.render(renderContext);
            await currentRenderTask.promise;
            currentRenderTask = null;

            // Create initial watermark at bottom center of page if not set
            // Wait a bit to ensure canvas is rendered
            setTimeout(() => {
                createInitialWatermark();
            }, 100);

        } catch (error) {
            if (console?.error) {
                console.error('Error rendering page:', error);
            }
        }
    }

    function createInitialWatermark() {
        if (!pdfDoc || pdfPageWidth === 0 || pdfPageHeight === 0) {
            // PDF not ready yet
            return;
        }

        // Set watermark at bottom center of page - position lower on mobile
        const isMobile = window.innerWidth <= 768;
        watermarkX = pdfPageWidth / 2; // Center horizontally
        watermarkY = isMobile ? 30 : 50; // Lower position on mobile (30 points from bottom)

        // Initialize rotation and scale if not already set
        if (watermarkRotation === undefined || isNaN(watermarkRotation) || watermarkRotation === null) {
            watermarkRotation = 0.0;
        }
        if (watermarkScale === undefined || isNaN(watermarkScale) || watermarkScale === null) {
            // Smaller scale on mobile for better UX
            watermarkScale = isMobile ? 0.8 : 1.0;
        }

        // Ensure watermark preview is visible
        watermarkPreview.classList.remove('hidden');

        // Update hidden inputs
        if (xInput) {
            xInput.value = watermarkX.toFixed(2);
        }
        if (yInput) {
            yInput.value = watermarkY.toFixed(2);
        }
        if (positionInput) positionInput.value = 'custom';
        if (rotationInput) rotationInput.value = (watermarkRotation || 0).toFixed(1);
        if (scaleInput) scaleInput.value = (watermarkScale || 1.0).toFixed(2);

        // Update preview
        updateWatermarkPreview();
    }

    // Pages option handlers for watermark
    const watermarkPagesAllRadio = document.getElementById('watermarkPagesAll');
    const watermarkPagesCurrentRadio = document.getElementById('watermarkPagesCurrent');
    const watermarkPagesCustomRadio = document.getElementById('watermarkPagesCustom');
    const watermarkPagesCustomInput = document.getElementById('watermarkPagesCustomInput');

    if (watermarkPagesAllRadio) {
        watermarkPagesAllRadio.addEventListener('change', () => {
            if (watermarkPagesCustomInput) {
                watermarkPagesCustomInput.disabled = true;
                watermarkPagesCustomInput.value = '';
            }
        });
    }

    if (watermarkPagesCurrentRadio) {
        watermarkPagesCurrentRadio.addEventListener('change', () => {
            if (watermarkPagesCustomInput) {
                watermarkPagesCustomInput.disabled = true;
                watermarkPagesCustomInput.value = '';
            }
        });
    }

    if (watermarkPagesCustomRadio && watermarkPagesCustomInput) {
        watermarkPagesCustomRadio.addEventListener('change', () => {
            watermarkPagesCustomInput.disabled = false;
            watermarkPagesCustomInput.focus();
        });
    }

    pageSelector.addEventListener('change', async (e) => {
        currentPage = parseInt(e.target.value);
        await renderPage(currentPage);
        // Watermark position will be maintained or recreated
    });

    // Click on canvas to set watermark position (only if not clicking on watermark)
    pdfCanvas.addEventListener('mousedown', (e) => {
        if (!pdfDoc) return;

        // Check if clicking on watermark preview or its handles
        const target = e.target;
        if (target.closest('#watermarkPreview')) {
            return; // Let watermark handle its own events
        }

        // Click outside watermark - set new position
        const rect = pdfCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Convert canvas coordinates to PDF points
        const scaleFactor = pdfPageWidth / canvasWidth;

        // X coordinate in points
        watermarkX = x * scaleFactor;

        // Y coordinate in points (flip because PDF uses bottom-left origin)
        watermarkY = (canvasHeight - y) * scaleFactor;

        // Initialize rotation and scale if not set
        if (watermarkRotation === undefined || isNaN(watermarkRotation)) {
            watermarkRotation = 0;
        }
        if (watermarkScale === undefined || isNaN(watermarkScale)) {
            watermarkScale = 1.0;
        }

        // Update hidden inputs
        if (xInput) xInput.value = watermarkX.toFixed(2);
        if (yInput) yInput.value = watermarkY.toFixed(2);
        if (positionInput) positionInput.value = 'custom';
        if (rotationInput) rotationInput.value = watermarkRotation.toFixed(1);
        if (scaleInput) scaleInput.value = watermarkScale.toFixed(2);

        // Update preview
        updateWatermarkPreview();
    });

    function updateWatermarkPreview() {
        if (!pdfDoc) {
            watermarkPreview.classList.add('hidden');
            return;
        }

        // Always create initial watermark if position not set
        if (watermarkX === null || watermarkY === null) {
            createInitialWatermark();
            return;
        }

        const isText = watermarkTypeText?.checked;
        const opacity = parseInt(opacitySlider?.value || 30) / 100;
        const color = watermarkColor?.value || '#000000';
        const fontSize = parseInt(fontSizeSlider?.value || 72);
        const text = watermarkText?.value || 'CONFIDENTIAL';

        console.log('Updating watermark preview with:', { isText, opacity, color, fontSize, text });

        // Convert PDF coordinates to canvas coordinates
        const scaleFactor = canvasWidth / pdfPageWidth;
        const canvasX = watermarkX * scaleFactor;
        const canvasY = canvasHeight - (watermarkY * scaleFactor); // Flip Y

        console.log('Canvas coordinates:', { canvasX, canvasY, scaleFactor });

        // Always ensure watermark is visible
        watermarkPreview.classList.remove('hidden');

        watermarkPreview.style.left = `${canvasX}px`;
        watermarkPreview.style.top = `${canvasY}px`;
        watermarkPreview.style.color = color;
        watermarkPreview.style.opacity = opacity;
        // Invert rotation: ReportLab rotates counter-clockwise, CSS rotates clockwise
        const cssRotation = -watermarkRotation;
        watermarkPreview.style.transform = `translate(-50%, -50%) rotate(${cssRotation}deg) scale(${watermarkScale})`;
        watermarkPreview.style.transformOrigin = 'center center';

        let content = '';
        if (isText) {
            // Scale font size to match PDF rendering
            // In PDF, font_size is in points, and we apply scale
            // In preview, we need to scale by canvas scale factor and watermark scale
            const scaledFontSize = fontSize * scaleFactor * watermarkScale;
            // Use bold font to match PDF (WatermarkFontBold or Helvetica-Bold)
            const displayText = text.trim() || 'CONFIDENTIAL'; // Use default if text is empty
            content = `<span class="watermark-preview-text" style="font-size: ${scaledFontSize}px; font-weight: bold; font-family: Arial, Helvetica, sans-serif;">${escapeHtml(displayText)}</span>`;
        } else if (watermarkImage) {
            // Scale image to match PDF rendering
            // In PDF: base_scale = min(page_width / img_width, page_height / img_height) * 0.5
            // Then: scaled_width = img_width * base_scale * scale
            // Convert PDF dimensions to canvas dimensions
            const pdfImgWidth = watermarkImage.width;
            const pdfImgHeight = watermarkImage.height;
            const baseScale = Math.min(pdfPageWidth / pdfImgWidth, pdfPageHeight / pdfImgHeight) * 0.5;
            const scaledPdfWidth = pdfImgWidth * baseScale * watermarkScale;
            const scaledPdfHeight = pdfImgHeight * baseScale * watermarkScale;
            // Convert to canvas pixels
            const imgWidth = scaledPdfWidth * scaleFactor;
            const imgHeight = scaledPdfHeight * scaleFactor;

            content = `<img src="${watermarkImage.src}" style="width: ${imgWidth}px; height: ${imgHeight}px; opacity: ${opacity};" alt="Watermark">`;
        } else {
            // Show placeholder when no watermark type is selected
            content = `<span class="watermark-preview-text" style="font-size: ${24 * scaleFactor}px; font-weight: bold; font-family: Arial, Helvetica, sans-serif; color: #ccc;">Select watermark type</span>`;
        }

        // Add corner handles for scaling only (rotation is done via slider)
        content += '<div class="watermark-handle corner nw" data-corner="nw"></div>';
        content += '<div class="watermark-handle corner ne" data-corner="ne"></div>';
        content += '<div class="watermark-handle corner sw" data-corner="sw"></div>';
        content += '<div class="watermark-handle corner se" data-corner="se"></div>';

        watermarkPreview.innerHTML = content;
        watermarkPreview.classList.remove('hidden');

        // Attach event handlers to handles
        attachWatermarkHandlers();
    }

    // Visual enhancement functions
    function createAlignmentGrid() {
        if (alignmentGrid) return;

        alignmentGrid = document.createElement('div');
        alignmentGrid.id = 'alignmentGrid';
        alignmentGrid.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
            z-index: 5;
        `;

        // Create grid lines
        const gridHTML = `
            <div style="position: absolute; top: 0; left: 50%; width: 1px; height: 100%; background: rgba(59, 130, 246, 0.3); transform: translateX(-50%);"></div>
            <div style="position: absolute; top: 50%; left: 0; width: 100%; height: 1px; background: rgba(59, 130, 246, 0.3); transform: translateY(-50%);"></div>
            <div style="position: absolute; top: 25%; left: 0; width: 100%; height: 1px; background: rgba(59, 130, 246, 0.15);"></div>
            <div style="position: absolute; top: 75%; left: 0; width: 100%; height: 1px; background: rgba(59, 130, 246, 0.15);"></div>
            <div style="position: absolute; top: 0; left: 25%; width: 1px; height: 100%; background: rgba(59, 130, 246, 0.15);"></div>
            <div style="position: absolute; top: 0; left: 75%; width: 1px; height: 100%; background: rgba(59, 130, 246, 0.15);"></div>
        `;

        alignmentGrid.innerHTML = gridHTML;
        pdfCanvasContainer.appendChild(alignmentGrid);
    }

    function showAlignmentGrid() {
        if (!alignmentGrid) createAlignmentGrid();
        alignmentGrid.style.opacity = '1';
        isShowingGrid = true;
    }

    function hideAlignmentGrid() {
        if (alignmentGrid) {
            alignmentGrid.style.opacity = '0';
        }
        isShowingGrid = false;
    }

    function snapToGrid(value, gridSize = 20) {
        return Math.round(value / gridSize) * gridSize;
    }

    function attachWatermarkHandlers() {
        const cornerHandles = watermarkPreview.querySelectorAll('.corner');

        const onPointerDownMove = (clientX, clientY, target) => {
            if (!pdfCanvas || !pdfDoc) return;
            const rect = pdfCanvas.getBoundingClientRect();
            isInteracting = true;

            // Check handles first
            // Corner handles - scaling only
            if (Array.from(cornerHandles).includes(target)) {
                isScaling = true;
                currentScaleCorner = target.dataset.corner;

                const scaleFactor = canvasWidth / pdfPageWidth;
                const centerX = watermarkX * scaleFactor;
                const centerY = canvasHeight - (watermarkY * scaleFactor);
                const startX = clientX - rect.left;
                const startY = clientY - rect.top;

                // Store initial position for scaling
                dragStartX = startX;
                dragStartY = startY;

                // Calculate initial distance from center to handle
                initialDistance = Math.sqrt(
                    Math.pow(startX - centerX, 2) + Math.pow(startY - centerY, 2)
                );
                initialScale = watermarkScale || 1.0;

                // Add visual feedback to handle
                target.style.transform = 'scale(1.2)';
                target.style.backgroundColor = 'rgba(59, 130, 246, 0.8)';
                return;
            }

            // Drag to move (click anywhere within watermark area, not on handles)
            if (target === watermarkPreview || target.closest('#watermarkPreview')) {
                isDraggingWatermark = true;
                dragStartX = clientX - rect.left;
                dragStartY = clientY - rect.top;

                // Show alignment grid when dragging starts
                showAlignmentGrid();

                // Add visual feedback
                watermarkPreview.style.transition = 'none';
                watermarkPreview.style.cursor = 'grabbing';
                return;
            }
        };

        // Mouse handlers
        watermarkPreview.addEventListener('mousedown', (e) => {
            if (!pdfCanvas || !pdfDoc) return;
            // Let handles handle their own events in shared logic
            onPointerDownMove(e.clientX, e.clientY, e.target);
            e.preventDefault();
        });

        cornerHandles.forEach(handle => {
            handle.addEventListener('mousedown', (e) => {
                if (!pdfCanvas || !pdfDoc) return;
                onPointerDownMove(e.clientX, e.clientY, handle);
                e.stopPropagation();
                e.preventDefault();
            });
        });

        // Touch handlers
        watermarkPreview.addEventListener('touchstart', (e) => {
            if (!pdfCanvas || !pdfDoc) return;
            const touch = e.touches[0];
            if (!touch) return;
            onPointerDownMove(touch.clientX, touch.clientY, e.target);
            e.preventDefault();
        }, { passive: false });

        cornerHandles.forEach(handle => {
            handle.addEventListener('touchstart', (e) => {
                if (!pdfCanvas || !pdfDoc) return;
                const touch = e.touches[0];
                if (!touch) return;
                onPointerDownMove(touch.clientX, touch.clientY, handle);
                e.stopPropagation();
                e.preventDefault();
            }, { passive: false });
        });

    }

    // Common movement handler to eliminate code duplication
    function handleMovement(x, y) {
        if (isDraggingWatermark) {
            // Move watermark with grid snapping
            const scaleFactor = pdfPageWidth / canvasWidth;
            let newX = x;
            let newY = y;

            // Apply grid snapping when near grid lines
            const snapThreshold = 10; // pixels
            const gridLines = [canvasWidth * 0.25, canvasWidth * 0.5, canvasWidth * 0.75,
                              canvasHeight * 0.25, canvasHeight * 0.5, canvasHeight * 0.75];

            // Snap to grid lines if close enough
            for (const gridLine of gridLines) {
                if (Math.abs(x - gridLine) < snapThreshold) {
                    newX = gridLine;
                    break;
                }
            }

            const deltaX = (newX - dragStartX) * scaleFactor;
            const deltaY = -(newY - dragStartY) * scaleFactor; // Flip Y

            watermarkX += deltaX;
            watermarkY += deltaY;

            // Constrain to canvas bounds
            watermarkX = Math.max(0, Math.min(watermarkX, pdfPageWidth));
            watermarkY = Math.max(0, Math.min(watermarkY, pdfPageHeight));

            if (xInput) xInput.value = watermarkX.toFixed(2);
            if (yInput) yInput.value = watermarkY.toFixed(2);

            dragStartX = newX;
            dragStartY = newY;
            updateWatermarkPreview();
        } else if (isScaling) {
            // Scaling only from corner handles
            const scaleFactor = canvasWidth / pdfPageWidth;
            const centerX = watermarkX * scaleFactor;
            const centerY = canvasHeight - (watermarkY * scaleFactor);

            const currentDistance = Math.sqrt(
                Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2)
            );

            const scaleRatio = currentDistance / initialDistance;

            // Calculate max scale based on page size to prevent watermark from exceeding page bounds
            let maxScale = 3.0;
            const isText = watermarkTypeText?.checked;
            if (isText) {
                // For text: estimate width based on font size and text length
                const fontSize = parseInt(fontSizeSlider?.value || 72);
                const text = watermarkText?.value || 'CONFIDENTIAL';
                const estimatedWidth = fontSize * text.length * 0.6; // Approximate character width
                const estimatedHeight = fontSize * 1.2;
                const maxScaleWidth = (pdfPageWidth * 0.95) / estimatedWidth;
                const maxScaleHeight = (pdfPageHeight * 0.95) / estimatedHeight;
                maxScale = Math.max(0.5, Math.min(maxScaleWidth, maxScaleHeight, 5.0));
            } else if (watermarkImage) {
                // For image: use actual image dimensions with base scale
                const baseScale = Math.min(pdfPageWidth / watermarkImage.width, pdfPageHeight / watermarkImage.height) * 0.5;
                const scaledWidth = watermarkImage.width * baseScale;
                const scaledHeight = watermarkImage.height * baseScale;
                const maxScaleWidth = (pdfPageWidth * 0.95) / scaledWidth;
                const maxScaleHeight = (pdfPageHeight * 0.95) / scaledHeight;
                maxScale = Math.max(0.5, Math.min(maxScaleWidth, maxScaleHeight, 5.0));
            }

            watermarkScale = Math.max(0.1, Math.min(maxScale, initialScale * scaleRatio));

            // Update scale slider
            const scaleSlider = document.getElementById('scale_slider');
            const scaleValueDisplay = document.getElementById('scaleValue');
            if (scaleSlider) {
                scaleSlider.value = watermarkScale;
                if (scaleValueDisplay) scaleValueDisplay.textContent = Math.round(watermarkScale * 100) + '%';
            }

            // Update hidden input
            if (scaleInput) scaleInput.value = watermarkScale.toFixed(2);

            updateWatermarkPreview();
        }
    }

    // Global mouse move handler
    document.addEventListener('mousemove', (e) => {
        if (!pdfDoc || watermarkX === null || watermarkY === null) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        handleMovement(x, y);
    });

    // Global touch move handler with pinch-to-zoom support
    document.addEventListener('touchmove', (e) => {
        if (!pdfDoc || watermarkX === null || watermarkY === null) return;

        // Handle pinch-to-zoom (two fingers)
        if (e.touches.length === 2 && isInteracting) {
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];

            const currentPinchDistance = Math.sqrt(
                Math.pow(touch2.clientX - touch1.clientX, 2) +
                Math.pow(touch2.clientY - touch1.clientY, 2)
            );

            if (!isPinching) {
                // Start pinch gesture
                isPinching = true;
                initialPinchDistance = currentPinchDistance;
                initialScale = watermarkScale;
            } else {
                // Calculate scale change
                const scaleRatio = currentPinchDistance / initialPinchDistance;

                // Calculate max scale
                let maxScale = 3.0;
                const isText = watermarkTypeText?.checked;
                if (isText) {
                    const fontSize = parseInt(fontSizeSlider?.value || 72);
                    const text = watermarkText?.value || 'CONFIDENTIAL';
                    const estimatedWidth = fontSize * text.length * 0.6;
                    const estimatedHeight = fontSize * 1.2;
                    const maxScaleWidth = (pdfPageWidth * 0.95) / estimatedWidth;
                    const maxScaleHeight = (pdfPageHeight * 0.95) / estimatedHeight;
                    maxScale = Math.max(0.5, Math.min(maxScaleWidth, maxScaleHeight, 5.0));
                } else if (watermarkImage) {
                    const baseScale = Math.min(pdfPageWidth / watermarkImage.width, pdfPageHeight / watermarkImage.height) * 0.5;
                    const scaledWidth = watermarkImage.width * baseScale;
                    const scaledHeight = watermarkImage.height * baseScale;
                    const maxScaleWidth = (pdfPageWidth * 0.95) / scaledWidth;
                    const maxScaleHeight = (pdfPageHeight * 0.95) / scaledHeight;
                    maxScale = Math.max(0.5, Math.min(maxScaleWidth, maxScaleHeight, 5.0));
                }

                watermarkScale = Math.max(0.1, Math.min(maxScale, initialScale * scaleRatio));

                // Update scale slider
                const scaleSlider = document.getElementById('scale_slider');
                const scaleValueDisplay = document.getElementById('scaleValue');
                if (scaleSlider) {
                    scaleSlider.value = watermarkScale;
                    if (scaleValueDisplay) scaleValueDisplay.textContent = Math.round(watermarkScale * 100) + '%';
                }

                // Update hidden input
                if (scaleInput) scaleInput.value = watermarkScale.toFixed(2);

                updateWatermarkPreview();
            }

            e.preventDefault();
            return;
        }

        // Single touch - handle drag/scale
        const touch = e.touches[0];
        if (!touch) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;

        if (isDraggingWatermark || isScaling) {
            handleMovement(x, y);
        }

        // Only prevent default when actively interacting with watermark
        if (isDraggingWatermark || isScaling || isPinching) {
            e.preventDefault();
        }
        // Allow normal scrolling when not interacting with watermark
    }, { passive: false });

    document.addEventListener('mouseup', () => {
        if (isInteracting) {
            // Reset interaction states
            isDraggingWatermark = false;
            isScaling = false;
            currentScaleCorner = null;
            isInteracting = false;

            // Hide visual helpers
            hideAlignmentGrid();

            // Reset watermark preview styles
            if (watermarkPreview) {
                watermarkPreview.style.transition = 'transform 0.2s ease';
                watermarkPreview.style.cursor = 'grab';
            }

            // Reset corner handles styles
            const cornerHandles = watermarkPreview?.querySelectorAll('.corner');
            if (cornerHandles) {
                cornerHandles.forEach(handle => {
                    handle.style.transform = 'scale(1)';
                    handle.style.backgroundColor = 'rgba(59, 130, 246, 0.6)';
                });
            }
        }
    });

    document.addEventListener('touchend', () => {
        if (isInteracting) {
            // Reset interaction states
            isDraggingWatermark = false;
            isScaling = false;
            isPinching = false;
            currentScaleCorner = null;
            isInteracting = false;

            // Hide visual helpers
            hideAlignmentGrid();

            // Reset watermark preview styles
            if (watermarkPreview) {
                watermarkPreview.style.transition = 'transform 0.2s ease';
            }

            // Reset corner handles styles
            const cornerHandles = watermarkPreview?.querySelectorAll('.corner');
            if (cornerHandles) {
                cornerHandles.forEach(handle => {
                    handle.style.transform = 'scale(1)';
                    handle.style.backgroundColor = 'rgba(59, 130, 246, 0.6)';
                });
            }
        }
    });

    // Use escapeHtml from utils.js
    const escapeHtml = window.escapeHtml || function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Ensure watermark position is set
        if (watermarkX === null || watermarkY === null) {
            createInitialWatermark();
        }

        if (watermarkX === null || watermarkY === null) {
            window.window.showError('Please wait for PDF to load, then adjust the watermark.', 'editorResult');
            return;
        }

        const formData = new FormData();
        const fieldName = window.FILE_INPUT_NAME || 'pdf_file';
        const selectedFile = fileInput?.files?.[0] || fileInputDrop?.files?.[0];

        if (!selectedFile) {
            window.window.showError(window.SELECT_FILE_MESSAGE || 'Please select a file', 'editorResult');
            return;
        }

        formData.append(fieldName, selectedFile);
        formData.append('position', positionInput.value || 'custom');

        // Ensure coordinates are valid numbers
        const xValue = parseFloat(xInput.value);
        const yValue = parseFloat(yInput.value);
        if (isNaN(xValue) || isNaN(yValue)) {
            window.window.showError('Invalid watermark position. Please click on the PDF to set the position.', 'editorResult');
            return;
        }

        formData.append('x', xValue.toFixed(2));
        formData.append('y', yValue.toFixed(2));
        formData.append('color', watermarkColor.value);
        formData.append('opacity', (parseInt(opacitySlider.value) / 100).toFixed(2));
        formData.append('rotation', (watermarkRotation || 0).toFixed(1));
        formData.append('scale', (watermarkScale || 1.0).toFixed(2));

        // Get pages value from radio buttons
        const watermarkPagesAllRadio = document.getElementById('watermarkPagesAll');
        const watermarkPagesCurrentRadio = document.getElementById('watermarkPagesCurrent');
        const watermarkPagesCustomRadio = document.getElementById('watermarkPagesCustom');
        const watermarkPagesCustomInput = document.getElementById('watermarkPagesCustomInput');

        let pagesValue = 'all';
        if (watermarkPagesCurrentRadio && watermarkPagesCurrentRadio.checked) {
            // Current page only
            pagesValue = currentPage.toString();
        } else if (watermarkPagesCustomRadio && watermarkPagesCustomRadio.checked && watermarkPagesCustomInput && watermarkPagesCustomInput.value.trim()) {
            // Custom pages
            pagesValue = watermarkPagesCustomInput.value.trim();
        } else {
            // All pages (default)
            pagesValue = 'all';
        }
        formData.append('pages', pagesValue);

        // Always append watermark_text (default if not provided)
        const textValue = watermarkText?.value || 'CONFIDENTIAL';
        formData.append('watermark_text', textValue);
        formData.append('font_size', fontSizeSlider?.value || 72);

        // Append watermark_file if image type is selected and file exists
        if (watermarkTypeImage?.checked && watermarkFile?.files?.[0]) {
            formData.append('watermark_file', watermarkFile.files[0]);
        }

        // Hide previous results
        hideResult();
        hideDownload();

        // Show loading
        window.showLoading('loadingContainer');

        // Disable form
        setFormDisabled(true);

        try {
            const response = await fetch(window.API_URL, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN
                },
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.log('Error data received:', errorData);
                console.log('Error data.error:', errorData.error);

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
            window.showDownloadButton(blob, selectedFile.name, 'downloadContainer', {
                successTitle: window.SUCCESS_TITLE || 'Editing Complete!',
                downloadButtonText: window.DOWNLOAD_BUTTON_TEXT || 'Download File',
                convertAnotherText: window.EDIT_ANOTHER_TEXT || 'Edit another file',
                onConvertAnother: () => {
                    const fileInput = document.getElementById('fileInput');
                    const fileInputDrop = document.getElementById('fileInputDrop');
                    const selectedFileDiv = document.getElementById('selectedFile');
                    const fileInfo = document.getElementById('fileInfo');
                    const editButton = document.getElementById('editButton');

                    if (fileInput) fileInput.value = '';
                    if (fileInputDrop) fileInputDrop.value = '';

                    if (selectedFileDiv) {
                        selectedFileDiv.classList.add('hidden');
                    }
                    if (fileInfo) {
                        fileInfo.classList.remove('hidden');
                    }

                    if (editButton) {
                        editButton.disabled = true;
                    }

                    // Hide preview sections
                    const pdfPreviewSection = document.getElementById('pdfPreviewSection');
                    const watermarkSettingsSection = document.getElementById('watermarkSettingsSection');
                    if (pdfPreviewSection) {
                        pdfPreviewSection.classList.add('hidden');
                    }
                    if (watermarkSettingsSection) {
                        watermarkSettingsSection.classList.add('hidden');
                    }

                    hideDownload();
                    hideResult();
                    setFormDisabled(false);

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
            window.window.showError(error.message || window.ERROR_MESSAGE, 'editorResult');
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

    function clearError() {
        if (resultContainer) {
            resultContainer.classList.add('hidden');
            resultContainer.innerHTML = '';
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
