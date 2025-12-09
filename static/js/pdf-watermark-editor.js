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
    let isDraggingWatermark = false;
    let isRotating = false;
    let isScaling = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let initialRotation = 0;
    let initialScale = 1.0;
    let initialDistance = 0;
    let dragStartAngle = 0;
    let currentScaleCorner = null;

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

    // Color picker sync
    if (watermarkColor && watermarkColorText) {
        watermarkColor.addEventListener('input', (e) => {
            watermarkColorText.value = e.target.value.toUpperCase();
            updateWatermarkPreview();
        });

        watermarkColorText.addEventListener('input', (e) => {
            const value = e.target.value;
            if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
                watermarkColor.value = value;
                updateWatermarkPreview();
            }
        });
    }

    // Opacity slider
    if (opacitySlider && opacityValue) {
        opacitySlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            opacityValue.textContent = `${value}%`;
            updateWatermarkPreview();
        });
    }

    // Font size slider
    if (fontSizeSlider && fontSizeValue) {
        fontSizeSlider.addEventListener('input', (e) => {
            fontSizeValue.textContent = e.target.value;
            updateWatermarkPreview();
        });
    }

    // Watermark text change - update preview in real-time
    if (watermarkText) {
        watermarkText.addEventListener('input', () => {
            // Force update preview when text changes
            if (pdfDoc && watermarkX !== null && watermarkY !== null) {
                updateWatermarkPreview();
            }
        });

        // Also update on blur (when user finishes editing)
        watermarkText.addEventListener('blur', () => {
            if (pdfDoc && watermarkX !== null && watermarkY !== null) {
                updateWatermarkPreview();
            }
        });
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
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                if (file.type === 'application/pdf') {
                    handleFileSelect(file);
                }
            }
        });
    }

    if (fileInputDrop) {
        fileInputDrop.addEventListener('change', (e) => {
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
            // Check if PDF.js is loaded
            if (typeof pdfjsLib === 'undefined') {
                showError('PDF.js library is not loaded. Please refresh the page and try again.');
                console.error('PDF.js library (pdfjsLib) is not available');
                return;
            }

            // Cleanup previous PDF if exists
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

            // Load PDF document with error handling
            pdfDoc = await pdfjsLib.getDocument({
                data: arrayBuffer,
                verbosity: 0 // Suppress warnings
            }).promise;

            if (!pdfDoc) {
                showError('Failed to load PDF document. Please check if the file is a valid PDF.');
                // Hide preview sections on load error
                pdfPreviewSection.classList.add('hidden');
                watermarkSettingsSection.classList.add('hidden');
                return;
            }

            pageCount = pdfDoc.numPages;

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
                if (watermarkX === null || watermarkY === null) {
                    createInitialWatermark();
                } else {
                    // Update watermark preview with existing position
                    updateWatermarkPreview();
                }
            }, 100);

        } catch (error) {
            showError('Failed to render PDF page.');
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error rendering page:', error);
            }
        }
    }

    function createInitialWatermark() {
        if (!pdfDoc || pdfPageWidth === 0 || pdfPageHeight === 0) {
            // PDF not ready yet
            return;
        }

        // Set watermark at bottom center of page
        watermarkX = pdfPageWidth / 2; // Center horizontally
        watermarkY = 50; // 50 points from bottom

        // Initialize rotation and scale if not already set
        if (watermarkRotation === undefined || isNaN(watermarkRotation) || watermarkRotation === null) {
            watermarkRotation = 0.0;
        }
        if (watermarkScale === undefined || isNaN(watermarkScale) || watermarkScale === null) {
            watermarkScale = 1.0;
        }

        // Update hidden inputs
        if (xInput) xInput.value = watermarkX.toFixed(2);
        if (yInput) yInput.value = watermarkY.toFixed(2);
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

        // If watermark position not set, create initial one
        if (watermarkX === null || watermarkY === null) {
            createInitialWatermark();
            return;
        }

        const isText = watermarkTypeText?.checked;
        const opacity = parseInt(opacitySlider?.value || 30) / 100;
        const color = watermarkColor?.value || '#000000';
        const fontSize = parseInt(fontSizeSlider?.value || 72);
        const text = watermarkText?.value || 'CONFIDENTIAL';

        // Convert PDF coordinates to canvas coordinates
        const scaleFactor = canvasWidth / pdfPageWidth;
        const canvasX = watermarkX * scaleFactor;
        const canvasY = canvasHeight - (watermarkY * scaleFactor); // Flip Y

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
            content = `<span class="watermark-preview-text" style="font-size: ${scaledFontSize}px; font-weight: bold; font-family: Arial, Helvetica, sans-serif;">${escapeHtml(text)}</span>`;
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
            watermarkPreview.classList.add('hidden');
            return;
        }

        // Add handles for rotation and scaling
        // Corner handles that do both rotation and scaling
        content += '<div class="watermark-handle corner nw" data-corner="nw"></div>';
        content += '<div class="watermark-handle corner ne" data-corner="ne"></div>';
        content += '<div class="watermark-handle corner sw" data-corner="sw"></div>';
        content += '<div class="watermark-handle corner se" data-corner="se"></div>';

        watermarkPreview.innerHTML = content;
        watermarkPreview.classList.remove('hidden');

        // Attach event handlers to handles
        attachWatermarkHandlers();
    }

    function attachWatermarkHandlers() {
        const cornerHandles = watermarkPreview.querySelectorAll('.corner');

        // Drag to move
        watermarkPreview.addEventListener('mousedown', (e) => {
            // Check if clicking on any handle
            if (Array.from(cornerHandles).includes(e.target)) {
                return; // Let handles handle their own events
            }

            isDraggingWatermark = true;
            const rect = pdfCanvas.getBoundingClientRect();
            dragStartX = e.clientX - rect.left;
            dragStartY = e.clientY - rect.top;
            e.preventDefault();
        });

        // Corner handles - combined rotation and scaling
        cornerHandles.forEach(handle => {
            handle.addEventListener('mousedown', (e) => {
                // Enable both rotation and scaling
                isRotating = true;
                isScaling = true;
                currentScaleCorner = handle.dataset.corner;

                const rect = pdfCanvas.getBoundingClientRect();
                const scaleFactor = canvasWidth / pdfPageWidth;
                const centerX = watermarkX * scaleFactor;
                const centerY = canvasHeight - (watermarkY * scaleFactor);
                const startX = e.clientX - rect.left;
                const startY = e.clientY - rect.top;

                // Calculate initial angle for rotation
                const startAngle = Math.atan2(startY - centerY, startX - centerX) * (180 / Math.PI);
                dragStartAngle = startAngle;
                initialRotation = watermarkRotation || 0;

                // Calculate initial distance for scaling
                initialDistance = Math.sqrt(
                    Math.pow(startX - centerX, 2) + Math.pow(startY - centerY, 2)
                );
                initialScale = watermarkScale || 1.0;

                dragStartX = startX;
                dragStartY = startY;

                e.stopPropagation();
                e.preventDefault();
            });
        });
    }

    // Global mouse move handler
    document.addEventListener('mousemove', (e) => {
        if (!pdfDoc || watermarkX === null || watermarkY === null) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (isDraggingWatermark) {
            // Move watermark
            const scaleFactor = pdfPageWidth / canvasWidth;
            const deltaX = (x - dragStartX) * scaleFactor;
            const deltaY = -(y - dragStartY) * scaleFactor; // Flip Y

            watermarkX += deltaX;
            watermarkY += deltaY;

            // Constrain to canvas bounds
            watermarkX = Math.max(0, Math.min(watermarkX, pdfPageWidth));
            watermarkY = Math.max(0, Math.min(watermarkY, pdfPageHeight));

            if (xInput) xInput.value = watermarkX.toFixed(2);
            if (yInput) yInput.value = watermarkY.toFixed(2);

            dragStartX = x;
            dragStartY = y;
            updateWatermarkPreview();
        } else if (isRotating && isScaling) {
            // Combined rotation and scaling from corner handle
            const scaleFactor = canvasWidth / pdfPageWidth;
            const centerX = watermarkX * scaleFactor;
            const centerY = canvasHeight - (watermarkY * scaleFactor);

            // Calculate current angle for rotation
            const currentAngle = Math.atan2(y - centerY, x - centerX) * (180 / Math.PI);
            let deltaAngle = currentAngle - dragStartAngle;

            // Handle angle wrap-around smoothly
            if (deltaAngle > 180) deltaAngle -= 360;
            if (deltaAngle < -180) deltaAngle += 360;

            watermarkRotation = initialRotation + deltaAngle;
            // Normalize rotation to -360 to 360
            while (watermarkRotation > 360) watermarkRotation -= 360;
            while (watermarkRotation < -360) watermarkRotation += 360;

            // Calculate current distance for scaling
            const currentDistance = Math.sqrt(
                Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2)
            );

            // Scale based on distance change
            const scaleRatio = currentDistance / initialDistance;
            watermarkScale = Math.max(0.1, Math.min(3.0, initialScale * scaleRatio));

            // Update hidden inputs
            if (rotationInput) rotationInput.value = watermarkRotation.toFixed(1);
            if (scaleInput) scaleInput.value = watermarkScale.toFixed(2);

            updateWatermarkPreview();
        } else if (isRotating) {
            // Rotate only (shouldn't happen with new design, but keep for safety)
            const scaleFactor = canvasWidth / pdfPageWidth;
            const centerX = watermarkX * scaleFactor;
            const centerY = canvasHeight - (watermarkY * scaleFactor);

            const currentAngle = Math.atan2(y - centerY, x - centerX) * (180 / Math.PI);
            let deltaAngle = currentAngle - dragStartAngle;

            if (deltaAngle > 180) deltaAngle -= 360;
            if (deltaAngle < -180) deltaAngle += 360;

            watermarkRotation = initialRotation + deltaAngle;
            while (watermarkRotation > 360) watermarkRotation -= 360;
            while (watermarkRotation < -360) watermarkRotation += 360;

            // Update hidden input
            if (rotationInput) rotationInput.value = watermarkRotation.toFixed(1);

            updateWatermarkPreview();
        } else if (isScaling) {
            // Scale only (shouldn't happen with new design, but keep for safety)
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
    });

    document.addEventListener('mouseup', () => {
        isDraggingWatermark = false;
        isRotating = false;
        isScaling = false;
        currentScaleCorner = null;
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

            const blob = await response.blob();

            if (!response.ok) {
                try {
                    const errorData = await blob.text();
                    const errorJson = JSON.parse(errorData);
                    throw new Error(errorJson.error || window.ERROR_MESSAGE);
                } catch {
                    throw new Error(window.ERROR_MESSAGE || 'Editing failed');
                }
            }

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
                        <a href="${url}"
                           download="${outputFileName}"
                           class="flex-1 inline-flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 active:scale-95">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                            </svg>
                            <span>${window.DOWNLOAD_BUTTON_TEXT || 'Download File'}</span>
                        </a>
                        <button type="button"
                                onclick="location.reload()"
                                class="flex-1 inline-flex items-center justify-center space-x-2 bg-white hover:bg-gray-50 text-gray-700 font-semibold py-3 px-6 rounded-xl border-2 border-gray-300 hover:border-gray-400 transition-all duration-200">
                            <span>${window.EDIT_ANOTHER_TEXT || 'Edit another file'}</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        container.classList.remove('hidden');
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
