/**
 * PDF Crop Editor Component
 * Visual PDF cropping with drag & drop selection
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

            // Load PDF
            const arrayBuffer = await file.arrayBuffer();
            pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            pageCount = pdfDoc.numPages;

            // Populate page selector
            pageSelector.innerHTML = '';
            for (let i = 1; i <= pageCount; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `Page ${i}`;
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
            showError('Failed to load PDF file. Please try again.');
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

            // Create initial selection covering entire page
            createInitialSelection();

        } catch (error) {
            showError('Failed to render PDF page.');
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error rendering page:', error);
            }
        }
    }

    function createInitialSelection() {
        // Create selection covering almost entire page with small margins
        // Use 5% margin on each side for better UX
        const marginX = canvasWidth * 0.05;
        const marginY = canvasHeight * 0.05;
        
        const initialX = marginX;
        const initialY = marginY;
        const initialWidth = canvasWidth - (marginX * 2);
        const initialHeight = canvasHeight - (marginY * 2);
        
        currentSelection = {
            x: initialX,
            y: initialY,
            width: initialWidth,
            height: initialHeight
        };
        
        updateSelection(initialX, initialY, initialWidth, initialHeight);
        cropSelection.classList.remove('hidden');
        updateCropCoordinates();
        updateOverlay(initialX, initialY, initialWidth, initialHeight);
        
        // Reset cursor
        pdfCanvas.style.cursor = 'crosshair';
        isMouseOverSelection = false;
        
        // Enable edit button
        if (editButton) {
            editButton.disabled = false;
            editButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
        
        // Show ready indicator
        if (cropReadyIndicator) {
            cropReadyIndicator.textContent = 'Crop area ready! Drag the box to move it, drag from outside to create a new selection, or use handles to resize.';
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

    // Reset cursor when mouse leaves canvas
    pdfCanvas.addEventListener('mouseleave', () => {
        pdfCanvas.style.cursor = 'crosshair';
        isMouseOverSelection = false;
    });

    // Add mousedown handler to cropSelection element for dragging
    if (cropSelection) {
        cropSelection.addEventListener('mousedown', (e) => {
            // Don't interfere with handles
            if (e.target && e.target.classList.contains('crop-handle')) {
                return;
            }
            
            if (!pdfDoc || !currentSelection || currentSelection.width <= 0 || currentSelection.height <= 0) {
                return;
            }
            
            const rect = pdfCanvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Start moving selection
            isDragging = true;
            dragStartX = x - currentSelection.x;
            dragStartY = y - currentSelection.y;
            pdfCanvas.style.cursor = 'grabbing';
            e.preventDefault();
            e.stopPropagation();
        });
    }

    pdfCanvas.addEventListener('mousedown', (e) => {
        if (!pdfDoc) return;

        const rect = pdfCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if clicking on a handle (handles have their own handlers and stopPropagation)
        const target = e.target;
        if (target && target.classList.contains('crop-handle')) {
            // Let handle logic handle it
            return;
        }
        
        // Check if clicking inside existing selection - allow moving it
        if (currentSelection && currentSelection.width > 0 && currentSelection.height > 0) {
            const isInside = x >= currentSelection.x && 
                           x <= currentSelection.x + currentSelection.width &&
                           y >= currentSelection.y && 
                           y <= currentSelection.y + currentSelection.height;
            
            if (isInside) {
                // Start moving selection
                isDragging = true;
                dragStartX = x - currentSelection.x;
                dragStartY = y - currentSelection.y;
                pdfCanvas.style.cursor = 'grabbing';
                e.preventDefault();
                return;
            }
        }
        
        // Start creating new selection (drag-to-select)
        isSelecting = true;
        selectionStartX = x;
        selectionStartY = y;
        pdfCanvas.style.cursor = 'crosshair';
        
        // Create temporary selection
        currentSelection = {
            x: x,
            y: y,
            width: 0,
            height: 0
        };
        
        cropSelection.classList.remove('hidden');
        updateSelection(x, y, 0, 0);
        
        // Show instruction
        if (cropReadyIndicator) {
            cropReadyIndicator.textContent = 'Drag to select crop area...';
            cropReadyIndicator.classList.remove('hidden');
        }
        
        e.preventDefault();
    });

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
            
            // Constrain to canvas bounds
            newX = Math.max(0, Math.min(newX, canvasWidth - currentSelection.width));
            newY = Math.max(0, Math.min(newY, canvasHeight - currentSelection.height));
            
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
            
            // Constrain to canvas bounds
            const selX = Math.max(0, Math.min(minX, canvasWidth - width));
            const selY = Math.max(0, Math.min(minY, canvasHeight - height));
            const selWidth = Math.min(width, canvasWidth - selX);
            const selHeight = Math.min(height, canvasHeight - selY);
            
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
                    cropReadyIndicator.textContent = 'Selection too small. Full page selected. Drag to create a new selection or drag the box to move it.';
                }
            } else if (currentSelection) {
                // Valid selection - update coordinates and show ready message
                updateCropCoordinates();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = 'Crop area selected! Drag the box to move it or use handles to resize. Click "Crop PDF" when ready.';
                }
            }
        } else if (isDragging) {
            isDragging = false;
            pdfCanvas.style.cursor = isMouseOverSelection ? 'move' : 'crosshair';
            // Update coordinates after dragging
            if (currentSelection) {
                updateCropCoordinates();
                if (cropReadyIndicator) {
                    cropReadyIndicator.textContent = 'Crop area moved! Drag again to reposition or use handles to resize. Click "Crop PDF" when ready.';
                }
            }
        }
    });

    function updateSelection(x, y, width, height) {
        // Ensure selection is within canvas bounds
        x = Math.max(0, Math.min(x, canvasWidth));
        y = Math.max(0, Math.min(y, canvasHeight));
        
        if (width < 0) {
            x += width;
            width = Math.abs(width);
        }
        if (height < 0) {
            y += height;
            height = Math.abs(height);
        }
        
        width = Math.min(width, canvasWidth - x);
        height = Math.min(height, canvasHeight - y);

        cropSelection.style.left = `${x}px`;
        cropSelection.style.top = `${y}px`;
        cropSelection.style.width = `${width}px`;
        cropSelection.style.height = `${height}px`;

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
        
        const scaleFactor = pdfPageWidth / canvasWidth;
        
        // X coordinate (left edge) in points
        const x = currentSelection.x * scaleFactor;
        
        // Y coordinate (bottom edge) in points
        // Need to flip Y because PDF uses bottom-left origin
        const y = (canvasHeight - currentSelection.y - currentSelection.height) * scaleFactor;
        
        // Width and height in points
        const width = currentSelection.width * scaleFactor;
        const height = currentSelection.height * scaleFactor;

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
            
            // Show ready indicator
            if (cropReadyIndicator) {
                cropReadyIndicator.classList.remove('hidden');
            }
        } else {
            // Hide ready indicator if not ready
            if (cropReadyIndicator) {
                cropReadyIndicator.classList.add('hidden');
            }
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

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!currentSelection || !document.getElementById('width').value) {
            showError('Please select the crop area by dragging on the PDF. The blue highlighted area will be kept.');
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
        const xValue = document.getElementById('x').value;
        const yValue = document.getElementById('y').value;
        const widthValue = document.getElementById('width').value;
        const heightValue = document.getElementById('height').value;
        
        // Ensure values are valid numbers
        if (!xValue || !yValue || !widthValue || !heightValue) {
            showError('Please adjust the crop area first.');
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
            // All pages (default)
            pagesValue = 'all';
        }
        formData.append('pages', pagesValue);

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
                            ${message}
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

