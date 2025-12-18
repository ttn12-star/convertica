/**
 * Organize PDF Tool
 * Simple approach like other PDF tools
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
    const pdfPreviewContainer = document.getElementById('pdfPreviewContainer');
    const editButton = document.getElementById('editButton');

    let pdfDoc = null;
    let pdfFile = null;
    let pageOrder = [];
    let draggedElement = null;
    let dragHandlers = new Map();

    // File input handlers - standard approach
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
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
            window.showError(window.SELECT_PDF_FILE || 'Please select a PDF file.', 'errorMessage');
            return;
        }

        // Store file reference but keep it in input for base template
        pdfFile = file;

        // Cleanup previous PDF if exists
        cleanupPreviousPDF();

        // Clear any previous errors when selecting a new file
        clearError();

        try {
            // Show preview section
            if (pdfPreviewSection) {
                pdfPreviewSection.classList.remove('hidden');
            }

            // Load PDF document
            const arrayBuffer = await file.arrayBuffer();
            pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

            // Universal page count validation
            const isValid = await window.validatePdfPageLimit(file);
            if (!isValid) {
                if (pdfPreviewSection) {
                    pdfPreviewSection.classList.add('hidden');
                }
                pdfDoc = null;
                return;
            }

            // Initialize page order (0-based indices)
            pageOrder = Array.from({ length: pdfDoc.numPages }, (_, i) => i);

            // Render all pages
            await renderAllPages();

            // Enable drag and drop
            makeSortable();

            // Enable edit button
            if (editButton) {
                editButton.disabled = false;
                editButton.classList.remove('opacity-50', 'cursor-not-allowed');
            }

        } catch (error) {
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error loading PDF:', error);
            }
            window.showError(window.FAILED_TO_LOAD_PDF || 'Failed to load PDF file. Please try again.', 'errorMessage');
        }
    }

    async function renderAllPages() {
        if (!pdfDoc || !pdfPreviewContainer) return;

        pdfPreviewContainer.innerHTML = '';

        // Render each page in the current order
        for (let i = 0; i < pageOrder.length; i++) {
            const pageIndex = pageOrder[i];
            await renderPage(pageIndex, i);
        }
    }

    async function renderPage(pageIndex, displayIndex) {
        let tempCanvas = null;
        try {
            const page = await pdfDoc.getPage(pageIndex + 1); // PDF.js uses 1-based indexing

            // Calculate thumbnail size (smaller than full size)
            const scale = 0.3; // 30% of original size
            const viewport = page.getViewport({ scale: scale });

            // Create preview card
            const card = document.createElement('div');
            card.className = 'pdf-page-card relative bg-white rounded-lg border-2 border-gray-300 p-2 cursor-move hover:border-blue-500 hover:shadow-md transition-all';
            card.draggable = true;
            card.dataset.pageIndex = pageIndex;
            card.dataset.displayIndex = displayIndex;

            // Create temporary canvas for rendering
            tempCanvas = document.createElement('canvas');
            tempCanvas.width = viewport.width;
            tempCanvas.height = viewport.height;
            const context = tempCanvas.getContext('2d');

            // Render page
            await page.render({
                canvasContext: context,
                viewport: viewport
            }).promise;

            // Card content
            card.innerHTML = `
                <div class="absolute top-2 left-2 bg-blue-600 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center z-10">
                    ${displayIndex + 1}
                </div>
                <div class="w-full overflow-hidden rounded">
                    <canvas class="w-full h-auto"></canvas>
                </div>
                <p class="text-xs text-gray-600 text-center mt-2">Page ${pageIndex + 1}</p>
            `;

            // Replace placeholder canvas with actual canvas
            const canvasContainer = card.querySelector('canvas');
            canvasContainer.width = tempCanvas.width;
            canvasContainer.height = tempCanvas.height;
            const canvasContext = canvasContainer.getContext('2d');
            canvasContext.drawImage(tempCanvas, 0, 0);

            pdfPreviewContainer.appendChild(card);

            // Cleanup temporary canvas
            tempCanvas = null;

        } catch (error) {
            if (typeof console !== 'undefined' && console.error) {
                console.error(`Error rendering page ${pageIndex + 1}:`, error);
            }
        } finally {
            // Ensure cleanup of temporary canvas
            if (tempCanvas) {
                const ctx = tempCanvas.getContext('2d');
                ctx.clearRect(0, 0, tempCanvas.width, tempCanvas.height);
                tempCanvas = null;
            }
        }
    }

    function makeSortable() {
        if (!pdfPreviewContainer) return;

        console.log('Organize PDF: Making sortable with HTML5 drag and drop');

        // Clean up previous drag handlers
        dragHandlers.forEach((handlers, element) => {
            handlers.forEach(handler => {
                element.removeEventListener(handler.event, handler.handler);
            });
        });
        dragHandlers.clear();

        const cards = pdfPreviewContainer.querySelectorAll('.pdf-page-card');
        console.log('Organize PDF: Found cards:', cards.length);

        cards.forEach(card => {
            // Skip if handlers already attached
            if (dragHandlers.has(card)) {
                return;
            }

            const handlers = [];

            const dragStartHandler = (e) => {
                console.log('Organize PDF: Drag started');
                draggedElement = card;
                card.style.opacity = '0.5';
                card.style.transform = 'scale(1.05) rotate(2deg)';
                card.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)';
                card.style.border = '2px solid #3b82f6';
                e.dataTransfer.effectAllowed = 'move';
            };

            const dragEndHandler = () => {
                console.log('Organize PDF: Drag ended');
                if (draggedElement) {
                    draggedElement.style.opacity = '1';
                    draggedElement.style.transform = '';
                    draggedElement.style.boxShadow = '';
                    draggedElement.style.border = '';
                }
                updateOrderFromPreview();
                draggedElement = null;
            };

            const dragOverHandler = (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';

                if (draggedElement && draggedElement !== card) {
                    const rect = card.getBoundingClientRect();
                    const midY = rect.top + rect.height / 2;

                    if (e.clientY < midY) {
                        pdfPreviewContainer.insertBefore(draggedElement, card);
                    } else {
                        pdfPreviewContainer.insertBefore(draggedElement, card.nextSibling);
                    }

                    // Update display indices in real-time
                    updateDisplayIndices();
                }
            };

            const dropHandler = (e) => {
                e.preventDefault();
                updateOrderFromPreview();
            };

            // Attach handlers
            card.addEventListener('dragstart', dragStartHandler);
            card.addEventListener('dragend', dragEndHandler);
            card.addEventListener('dragover', dragOverHandler);
            card.addEventListener('drop', dropHandler);

            // Store handlers for cleanup
            handlers.push(
                { event: 'dragstart', handler: dragStartHandler },
                { event: 'dragend', handler: dragEndHandler },
                { event: 'dragover', handler: dragOverHandler },
                { event: 'drop', handler: dropHandler }
            );
            dragHandlers.set(card, handlers);
        });
    }

    function updateDisplayIndices() {
        const cards = pdfPreviewContainer.querySelectorAll('.pdf-page-card');

        // Update visual display indices in real-time
        cards.forEach((card, index) => {
            const label = card.querySelector('.absolute.top-2.left-2');
            if (label) {
                label.textContent = `${index + 1}`;
            }
            card.dataset.displayIndex = index;
        });
    }

    function updateOrderFromPreview() {
        const cards = pdfPreviewContainer.querySelectorAll('.pdf-page-card');
        pageOrder = Array.from(cards).map(card => parseInt(card.dataset.pageIndex));

        // Update display indices
        updateDisplayIndices();

        // Debug logging
        if (typeof console !== 'undefined' && console.log) {
            console.log('Page order updated:', pageOrder);
        }
    }

    function updatePageNumbers() {
        const containers = pdfPreviewContainer.querySelectorAll('[data-page-index]');

        // Update visual page numbers in real-time
        containers.forEach((container, index) => {
            const label = container.querySelector('.absolute.top-2.left-2');
            if (label) {
                label.textContent = `${index + 1}`;
            }
        });
    }

    function updatePageOrder() {
        const containers = pdfPreviewContainer.querySelectorAll('[data-page-index]');
        pageOrder = Array.from(containers).map(container => parseInt(container.dataset.originalIndex));

        // Update page numbers
        updatePageNumbers();

        // Debug logging
        if (typeof console !== 'undefined' && console.log) {
            console.log('Page order updated:', pageOrder);
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

        // Clear preview container
        if (pdfPreviewContainer) {
            pdfPreviewContainer.innerHTML = '';
        }

        // Clear page order
        pageOrder = [];

        // Hide preview section
        if (pdfPreviewSection) {
            pdfPreviewSection.classList.add('hidden');
        }

        // Disable edit button
        if (editButton) {
            editButton.disabled = true;
            editButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    function clearError() {
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) {
            errorMessage.classList.add('hidden');
            errorMessage.textContent = '';
        }
    }

    // Custom form submission like pdf-crop-editor.js
    if (form && editButton) {
        let isSubmitting = false;

        // Handle button click instead of form submit to bypass base template
        editButton.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            if (isSubmitting) {
                console.log('Organize PDF: Already submitting, preventing duplicate');
                return false;
            }

            if (!pdfFile || !pdfDoc) {
                window.showError(window.SELECT_PDF_FIRST || 'Please select a PDF file first.', 'errorMessage');
                return false;
            }

            isSubmitting = true;

            // Show loading and disable form
            if (editButton) {
                editButton.disabled = true;
                const buttonText = editButton.querySelector('span span') || editButton;
                buttonText.dataset.originalText = buttonText.textContent;
                buttonText.textContent = window.ORGANIZING || 'Organizing...';
            }

            // Get API URL
            const apiUrl = window.API_URL || form.action || '/api/pdf-organize/organize/';

            // Create FormData
            const formData = new FormData();
            const fieldName = window.FILE_INPUT_NAME || 'pdf_file';
            const selectedFile = fileInput?.files?.[0] || fileInputDrop?.files?.[0];

            if (!selectedFile) {
                window.showError(window.SELECT_FILE_MESSAGE || 'Please select a file', 'errorMessage');
                isSubmitting = false;
                return;
            }

            formData.append(fieldName, selectedFile);
            formData.append('page_order', JSON.stringify(pageOrder));

            // Add CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfToken) {
                formData.append('csrfmiddlewaretoken', csrfToken.value);
            }

            try {
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || errorData.message || `Server error: ${response.status}`);
                }

                const blob = await response.blob();

                // Create resultContainer if it doesn't exist
                let resultContainer = document.getElementById('resultContainer');
                if (!resultContainer) {
                    resultContainer = document.createElement('div');
                    resultContainer.id = 'resultContainer';
                    resultContainer.className = 'mt-6';
                    form.parentNode.insertBefore(resultContainer, form.nextSibling);
                } else {
                    // Clear existing content to prevent duplicate buttons
                    resultContainer.innerHTML = '';
                }

                // Show download button like pdf-crop-editor.js
                window.showDownloadButton(blob, pdfFile.name, 'resultContainer', {
                    successTitle: 'Organization Complete!',
                    downloadButtonText: 'Download Organized PDF',
                    convertAnotherText: 'Organize another file',
                    onConvertAnother: () => {
                        console.log('Organize PDF: onConvertAnother called');
                        // Reset form
                        pdfFile = null;
                        pdfDoc = null;
                        pageOrder = [];
                        if (fileInput) fileInput.value = '';
                        if (fileInputDrop) fileInputDrop.value = '';
                        if (pdfPreviewSection) pdfPreviewSection.classList.add('hidden');
                        cleanupPreviousPDF();

                        // Hide result container
                        if (resultContainer) {
                            resultContainer.classList.add('hidden');
                            resultContainer.innerHTML = '';
                        }

                        window.scrollTo({ top: 0, behavior: 'smooth' });
                        setTimeout(() => {
                            const selectFileButton = document.getElementById('selectFileButton');
                            if (selectFileButton) selectFileButton.focus({ preventScroll: true });
                        }, 800);
                    }
                });

            } catch (error) {
                window.showError(`${window.FAILED_TO_ORGANIZE || 'Failed to organize PDF'}: ${error.message}`, 'errorMessage');
            } finally {
                // Restore button and reset submitting flag
                isSubmitting = false;
                if (editButton) {
                    editButton.disabled = false;
                    const buttonText = editButton.querySelector('span span') || editButton;
                    if (buttonText.dataset.originalText) {
                        buttonText.textContent = buttonText.dataset.originalText;
                    }
                }
            }
        });
    }
});
