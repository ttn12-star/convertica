/**
 * PDF Watermark Editor Component
 * Visual PDF watermark positioning with color and opacity controls
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set up PDF.js worker
    if (typeof pdfjsLib !== 'undefined') {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
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
    let initialRotation = 0.0; // Add missing initialRotation variable
    // Watermark interaction states
    let isDraggingWatermark = false;
    let isRotating = false;
    let isScaling = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let currentScaleCorner = null;
    let isInteracting = false; // Track if user is actively interacting

    // Visual enhancement elements
    let alignmentGrid = null;
    let rotationIndicator = null;
    let isShowingGrid = false;
    let initialScale = 1.0;
    let initialDistance = 0;
    let dragStartAngle = 0;

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
                    console.log('File selected via change event:', file.name);
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
                    console.log('File selected via drop change event:', file.name);
                    handleFileSelect(file);
                }
            }
        });
    }

    async function handleFileSelect(file) {
        try {
            // Clear any previous errors when selecting a new file
            clearError();

            if (typeof pdfjsLib === 'undefined') {
                showError('PDF.js library is not loaded. Please refresh the page and try again.');
                return;
            }
            cleanupPreviousPDF();

            // Show preview section
            pdfPreviewSection.classList.remove('hidden');
            watermarkSettingsSection.classList.remove('hidden');

            // Validate file type
            if (!file || !file.type || !file.type.includes('pdf')) {
                showError('Please select a valid PDF file.');
                // Hide preview sections on validation error
                pdfPreviewSection.classList.add('hidden');
                watermarkSettingsSection.classList.add('hidden');
                return;
            }

            // Small delay to ensure file is ready
            await new Promise(resolve => setTimeout(resolve, 50));

            // Load PDF
            const arrayBuffer = await file.arrayBuffer();

            // Check if arrayBuffer is valid
            if (!arrayBuffer || arrayBuffer.byteLength === 0) {
                showError('Failed to read file. Please try again.');
                // Hide preview sections on validation error
                pdfPreviewSection.classList.add('hidden');
                watermarkSettingsSection.classList.add('hidden');
                return;
            }

            // Load PDF document with retry mechanism for mobile devices
            let retryCount = 0;
            const maxRetries = 3;

            while (retryCount < maxRetries) {
                try {
                    console.log(`Loading PDF attempt ${retryCount + 1}/${maxRetries}`);

                    pdfDoc = await pdfjsLib.getDocument({
                        data: arrayBuffer,
                        verbosity: 0 // Suppress warnings
                    }).promise;

                    if (!pdfDoc) {
                        throw new Error('PDF document is null');
                    }

                    console.log('PDF loaded successfully');
                    break; // Success, exit retry loop

                } catch (error) {
                    retryCount++;
                    console.error(`PDF load attempt ${retryCount} failed:`, error);

                    if (retryCount >= maxRetries) {
                        showError('Failed to load PDF file. Please try again.');
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

            showError(errorMessage);
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
        isRotating = false;
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

            // Render PDF page
            const renderContext = {
                canvasContext: pdfCanvas.getContext('2d'),
                viewport: scaledViewport
            };

            await page.render(renderContext).promise;

            // Create initial watermark at bottom center of page if not set
            // Wait a bit to ensure canvas is rendered
            setTimeout(() => {
                console.log('PDF rendered, creating watermark...');
                createInitialWatermark();
            }, 100);

        } catch (error) {
            if (console?.error) {
                console.error('Error rendering page:', error);
            }
        }
    }

    function createInitialWatermark() {
        console.log('createInitialWatermark called', { pdfDoc, pdfPageWidth, pdfPageHeight });

        if (!pdfDoc || pdfPageWidth === 0 || pdfPageHeight === 0) {
            // PDF not ready yet
            console.log('PDF not ready, skipping watermark creation');
            return;
        }

        // Set watermark at bottom center of page - position lower on mobile
        const isMobile = window.innerWidth <= 768;
        watermarkX = pdfPageWidth / 2; // Center horizontally
        watermarkY = isMobile ? 30 : 50; // Lower position on mobile (30 points from bottom)

        console.log('Setting watermark position:', { watermarkX, watermarkY, isMobile });

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
        console.log('Updating inputs:', { xInput, yInput, positionInput, rotationInput, scaleInput });
        if (xInput) {
            xInput.value = watermarkX.toFixed(2);
            console.log('xInput set to:', xInput.value);
        }
        if (yInput) {
            yInput.value = watermarkY.toFixed(2);
            console.log('yInput set to:', yInput.value);
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
        console.log('updateWatermarkPreview called', { pdfDoc, watermarkX, watermarkY });

        if (!pdfDoc) {
            watermarkPreview.classList.add('hidden');
            return;
        }

        // Always create initial watermark if position not set
        if (watermarkX === null || watermarkY === null) {
            console.log('Watermark position not set, creating initial watermark');
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

        // Add handles for rotation and scaling
        // Corner handles for scaling only
        content += '<div class="watermark-handle corner nw" data-corner="nw"></div>';
        content += '<div class="watermark-handle corner ne" data-corner="ne"></div>';
        content += '<div class="watermark-handle corner sw" data-corner="sw"></div>';
        content += '<div class="watermark-handle corner se" data-corner="se"></div>';

        // Rotation handle near top-right corner with rotate icon
        content += '<div class="watermark-handle rotation-handle" title="Rotate" style="position: absolute; top: -18px; right: -18px; width: 16px; height: 16px; background: rgba(239, 68, 68, 0.6); border: 2px solid white; border-radius: 50%; cursor: grab; z-index: 10; display: flex; align-items: center; justify-content: center; font-size: 10px; color: white;">↻</div>';

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

    function createRotationIndicator() {
        if (rotationIndicator) return;

        rotationIndicator = document.createElement('div');
        rotationIndicator.id = 'rotationIndicator';
        rotationIndicator.style.cssText = `
            position: absolute;
            width: 60px;
            height: 60px;
            border: 2px dashed rgba(59, 130, 246, 0.6);
            border-radius: 50%;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
            z-index: 6;
        `;

        // Add rotation lines
        rotationIndicator.innerHTML = `
            <div style="position: absolute; top: 50%; left: 0; width: 100%; height: 1px; background: rgba(59, 130, 246, 0.4); transform: translateY(-50%);"></div>
            <div style="position: absolute; top: 0; left: 50%; width: 1px; height: 100%; background: rgba(59, 130, 246, 0.4); transform: translateX(-50%);"></div>
        `;

        pdfCanvasContainer.appendChild(rotationIndicator);
    }

    function showRotationIndicator(x, y) {
        if (!rotationIndicator) createRotationIndicator();
        rotationIndicator.style.left = (x - 30) + 'px';
        rotationIndicator.style.top = (y - 30) + 'px';
        rotationIndicator.style.opacity = '1';
    }

    function hideRotationIndicator() {
        if (rotationIndicator) {
            rotationIndicator.style.opacity = '0';
        }
    }

    function snapToGrid(value, gridSize = 20) {
        return Math.round(value / gridSize) * gridSize;
    }

    function attachWatermarkHandlers() {
        const cornerHandles = watermarkPreview.querySelectorAll('.corner');
        const rotationHandle = watermarkPreview.querySelector('.rotation-handle');

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

            // Rotation handle - rotation only
            if (target.classList.contains('rotation-handle')) {
                isRotating = true;

                const scaleFactor = canvasWidth / pdfPageWidth;
                const centerX = watermarkX * scaleFactor;
                const centerY = canvasHeight - (watermarkY * scaleFactor);
                const startX = clientX - rect.left;
                const startY = clientY - rect.top;

                // Store initial position and rotation for rotation
                dragStartX = startX;
                dragStartY = startY;
                initialRotation = watermarkRotation || 0;

                // Calculate and store initial angle from center to handle
                dragStartAngle = Math.atan2(startY - centerY, startX - centerX) * (180 / Math.PI);

                // Show rotation indicator
                showRotationIndicator(centerX, centerY);

                // Add visual feedback to rotation handle
                target.style.transform = 'scale(1.2)';
                target.style.backgroundColor = 'rgba(239, 68, 68, 0.8)';
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

        // Rotation handle handlers
        if (rotationHandle) {
            rotationHandle.addEventListener('mousedown', (e) => {
                if (!pdfCanvas || !pdfDoc) return;
                onPointerDownMove(e.clientX, e.clientY, rotationHandle);
                e.stopPropagation();
                e.preventDefault();
            });
        }

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

        // Rotation handle touch handlers
        if (rotationHandle) {
            rotationHandle.addEventListener('touchstart', (e) => {
                if (!pdfCanvas || !pdfDoc) return;
                const touch = e.touches[0];
                if (!touch) return;
                onPointerDownMove(touch.clientX, touch.clientY, rotationHandle);
                e.stopPropagation();
                e.preventDefault();
            }, { passive: false });
        }
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
        } else if (isRotating) {
            // Rotation only from rotation handle
            const scaleFactor = canvasWidth / pdfPageWidth;
            const centerX = watermarkX * scaleFactor;
            const centerY = canvasHeight - (watermarkY * scaleFactor);

            // Calculate angle from center to current cursor position
            const currentAngle = Math.atan2(y - centerY, x - centerX) * (180 / Math.PI);

            // Calculate initial angle from center to starting position
            const startAngle = Math.atan2(dragStartY - centerY, dragStartX - centerX) * (180 / Math.PI);

            // Calculate rotation change with reduced sensitivity and correct direction
            let rotationChange = startAngle - currentAngle; // Reversed for correct direction
            rotationChange *= 0.15; // Further reduce sensitivity for very smooth rotation

            // Add smoothing to prevent sudden jumps
            const maxChangePerFrame = 2.0; // Max 2 degrees per frame
            rotationChange = Math.max(-maxChangePerFrame, Math.min(maxChangePerFrame, rotationChange));

            // Handle angle wrap-around for smooth rotation
            if (rotationChange > 180) rotationChange -= 360;
            if (rotationChange < -180) rotationChange += 360;

            // Apply rotation with smooth transitions
            let newRotation = initialRotation + rotationChange;

            // Normalize angle to 0-360 range
            while (newRotation > 360) newRotation -= 360;
            while (newRotation < 0) newRotation += 360;

            watermarkRotation = newRotation;

            // Update hidden input
            if (rotationInput) rotationInput.value = watermarkRotation.toFixed(1);

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
            watermarkScale = Math.max(0.1, Math.min(3.0, initialScale * scaleRatio));

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

    // Global touch move handler
    document.addEventListener('touchmove', (e) => {
        if (!pdfDoc || watermarkX === null || watermarkY === null) return;
        const touch = e.touches[0];
        if (!touch) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;

        if (isDraggingWatermark || isRotating || isScaling) {
            handleMovement(x, y);
        }

        // Only prevent default when actively interacting with watermark
        if (isDraggingWatermark || isRotating || isScaling) {
            e.preventDefault();
        }
        // Allow normal scrolling when not interacting with watermark
    }, { passive: false });

    document.addEventListener('mouseup', () => {
        if (isInteracting) {
            // Reset interaction states
            isDraggingWatermark = false;
            isRotating = false;
            isScaling = false;
            currentScaleCorner = null;
            isInteracting = false;

            // Hide visual helpers
            hideAlignmentGrid();
            hideRotationIndicator();

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

            // Reset rotation handle styles
            const rotationHandle = watermarkPreview?.querySelector('.rotation-handle');
            if (rotationHandle) {
                rotationHandle.style.transform = 'scale(1)';
                rotationHandle.style.backgroundColor = 'rgba(239, 68, 68, 0.6)';
            }
        }
    });

    document.addEventListener('touchend', () => {
        if (isInteracting) {
            // Reset interaction states
            isDraggingWatermark = false;
            isRotating = false;
            isScaling = false;
            currentScaleCorner = null;
            isInteracting = false;

            // Hide visual helpers
            hideAlignmentGrid();
            hideRotationIndicator();

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

            // Reset rotation handle styles
            const rotationHandle = watermarkPreview?.querySelector('.rotation-handle');
            if (rotationHandle) {
                rotationHandle.style.transform = 'scale(1)';
                rotationHandle.style.backgroundColor = 'rgba(239, 68, 68, 0.6)';
            }
        }
    });

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Ensure watermark position is set
        if (watermarkX === null || watermarkY === null) {
            createInitialWatermark();
        }

        if (watermarkX === null || watermarkY === null) {
            showError('Please wait for PDF to load, then adjust the watermark.');
            return;
        }

        const formData = new FormData();
        const fieldName = window.FILE_INPUT_NAME || 'pdf_file';
        const selectedFile = fileInput?.files?.[0] || fileInputDrop?.files?.[0];

        if (!selectedFile) {
            showError(window.SELECT_FILE_MESSAGE || 'Please select a file');
            return;
        }

        formData.append(fieldName, selectedFile);
        formData.append('position', positionInput.value || 'custom');

        // Ensure coordinates are valid numbers
        const xValue = parseFloat(xInput.value);
        const yValue = parseFloat(yInput.value);
        if (isNaN(xValue) || isNaN(yValue)) {
            showError('Invalid watermark position. Please click on the PDF to set the position.');
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
        showLoading();

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
            hideLoading();
            showDownloadButton(selectedFile.name, blob);
            setFormDisabled(false);

        } catch (error) {
            hideLoading();
            showError(error.message || window.ERROR_MESSAGE);
            setFormDisabled(false);
        }
    });

    function showLoading() {
        const container = document.getElementById('loadingContainer');
        if (!container) return;

        container.innerHTML = `
            <div class="bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-200 rounded-xl p-6 sm:p-8 text-center animate-fade-in">
                <div class="flex flex-col items-center space-y-4">
                    <div class="relative">
                        <div class="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                    </div>
                    <div>
                        <h3 class="text-lg sm:text-xl font-bold text-gray-900 mb-2">
                            ${window.LOADING_TITLE || 'Processing your file...'}
                        </h3>
                        <p class="text-sm sm:text-base text-gray-600">
                            ${window.LOADING_MESSAGE || 'Please wait, this may take a few moments'}
                        </p>
                    </div>
                </div>
            </div>
        `;
        container.classList.remove('hidden');
    }

    function hideLoading() {
        const container = document.getElementById('loadingContainer');
        if (container) {
            container.classList.add('hidden');
        }
    }

    function showDownloadButton(originalFileName, blob) {
        const container = document.getElementById('downloadContainer');
        if (!container) return;

        const replaceRegex = new RegExp(window.REPLACE_REGEX || '\\.pdf$');
        const replaceTo = window.REPLACE_TO || '.pdf';
        const outputFileName = originalFileName.replace(replaceRegex, replaceTo);

        const url = URL.createObjectURL(blob);

        container.innerHTML = `
            <div class="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 sm:p-8 text-center animate-fade-in">
                <div class="flex flex-col items-center space-y-4">
                    <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                        <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-lg sm:text-xl font-bold text-gray-900 mb-2">
                            ${window.SUCCESS_TITLE || 'Editing Complete!'}
                        </h3>
                        <p class="text-sm sm:text-base text-gray-600 mb-4">
                            ${window.SUCCESS_MESSAGE || 'Your file is ready to download'}
                        </p>
                        <p class="text-xs text-gray-500 font-mono break-all px-2">
                            ${outputFileName}
                        </p>
                    </div>
                    <div class="flex flex-col sm:flex-row gap-3 w-full max-w-md">
                        <button id="downloadButton"
                                class="flex-1 inline-flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 active:scale-95">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                            </svg>
                            <span>${window.DOWNLOAD_BUTTON_TEXT || 'Download File'}</span>
                        </button>
                        <button type="button"
                                id="editAnotherButton"
                                class="flex-1 inline-flex items-center justify-center space-x-2 bg-white hover:bg-gray-50 text-gray-700 font-semibold py-3 px-6 rounded-xl border-2 border-gray-300 hover:border-gray-400 transition-all duration-200">
                            <span>${window.EDIT_ANOTHER_TEXT || 'Edit another file'}</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        container.classList.remove('hidden');

        // Scroll to download button
        setTimeout(() => {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);

        // Download button handler with showSaveFilePicker
        const downloadBtn = document.getElementById('downloadButton');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', async () => {
                const originalExt = outputFileName.includes('.') ? outputFileName.slice(outputFileName.lastIndexOf('.')) : '.pdf';
                let finalName = outputFileName;

                // Try modern file picker to let user choose directory & filename
                if (window.showSaveFilePicker) {
                    try {
                        const handle = await window.showSaveFilePicker({
                            suggestedName: outputFileName,
                            types: [{ description: 'PDF File', accept: { 'application/pdf': ['.pdf'] } }],
                        });
                        const writable = await handle.createWritable();
                        await writable.write(blob);
                        await writable.close();
                        finalName = handle.name || outputFileName;
                        downloadBtn.classList.add('bg-green-700');
                        downloadBtn.innerHTML = '<span>✓ ' + (window.DOWNLOAD_BUTTON_TEXT || 'Download File') + '</span>';
                        setTimeout(() => {
                            downloadBtn.classList.remove('bg-green-700');
                            downloadBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg><span>' + (window.DOWNLOAD_BUTTON_TEXT || 'Download File') + '</span>';
                        }, 2000);
                        return;
                    } catch (err) {
                        if (err.name !== 'AbortError') {
                            console.warn('File picker failed, falling back to direct download:', err);
                        } else {
                            // User cancelled
                            return;
                        }
                    }
                }

                // Fallback: prompt for filename, then trigger download (browser will ask location)
                const input = prompt(window.SAVE_AS_PROMPT || 'Save file as', outputFileName);
                if (input && input.trim()) {
                    finalName = input.trim();
                    const originalExt = outputFileName.includes('.') ? outputFileName.slice(outputFileName.lastIndexOf('.')) : '.pdf';
                    if (originalExt && !finalName.toLowerCase().endsWith(originalExt.toLowerCase())) {
                        finalName += originalExt;
                    }
                }

                const a = document.createElement('a');
                a.href = url;
                a.download = finalName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            });
        }

        // Edit another button handler with smooth scroll to top
        const editAnotherBtn = document.getElementById('editAnotherButton');
        if (editAnotherBtn) {
            editAnotherBtn.addEventListener('click', () => {
                // Hide selected file display
                const selectedFileDiv = document.getElementById('selectedFile');
                if (selectedFileDiv) {
                    selectedFileDiv.classList.add('hidden');
                }

                // Reset file input
                const fileInput = document.getElementById('fileInput');
                if (fileInput) {
                    fileInput.value = '';
                }

                // Reset watermark options
                const watermarkText = document.getElementById('watermarkText');
                const watermarkOpacity = document.getElementById('watermarkOpacity');
                const watermarkRotation = document.getElementById('watermarkRotation');
                if (watermarkText) watermarkText.value = '';
                if (watermarkOpacity) watermarkOpacity.value = '50';
                if (watermarkRotation) watermarkRotation.value = '45';

                // Hide download container
                hideDownload();

                // Clear PDF preview
                cleanupPreviousPDF();
                if (pdfPreviewSection) {
                    pdfPreviewSection.classList.add('hidden');
                }

                // Smooth scroll to top of page
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });

                // Focus on select button after scroll completes
                setTimeout(() => {
                    const selectFileButton = document.getElementById('selectFileButton');
                    if (selectFileButton) {
                        selectFileButton.focus();
                    }
                }, 800); // Wait for smooth scroll to complete
            });
        }
    }

    function hideDownload() {
        const container = document.getElementById('downloadContainer');
        if (container) {
            container.classList.add('hidden');
        }
    }

    function showError(message) {
        if (!resultContainer) return;

        resultContainer.innerHTML = `
            <div class="bg-red-50 border-2 border-red-200 rounded-xl p-6 text-center animate-fade-in">
                <div class="flex flex-col items-center space-y-3">
                    <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                        <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-lg font-bold text-red-900 mb-1">
                            ${window.ERROR_TITLE || 'Error'}
                        </h3>
                        <p class="text-sm text-red-700">
                            ${escapeHtml(message)}
                        </p>
                    </div>
                </div>
            </div>
        `;
        resultContainer.classList.remove('hidden');
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
