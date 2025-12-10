/**
 * Organize PDF Component
 * Handles PDF file selection, page thumbnails display, drag-and-drop reordering, and submission
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('editorForm') || document.getElementById('converterForm');
    if (!form) return;

    const fileInput = document.getElementById('fileInput');
    const fileInputDrop = document.getElementById('fileInputDrop');
    const selectFileButton = document.getElementById('selectFileButton');
    const pdfPreviewSection = document.getElementById('pdfPreviewSection');
    const pdfPreviewContainer = document.getElementById('pdfPreviewContainer');
    const editButton = document.getElementById('editButton');

    // Store PDF data
    let pdfDoc = null;
    let pdfFile = null;
    let pageOrder = []; // Array of page indices (0-based)
    let draggedElement = null;
    let dragHandlers = new Map(); // Store drag handlers for cleanup

    // Initialize PDF.js worker
    if (typeof pdfjsLib !== 'undefined') {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }

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
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
            showError(window.SELECT_PDF_FILE || 'Please select a PDF file.');
            return;
        }

        // Cleanup previous PDF if exists
        cleanupPreviousPDF();

        // Store file reference for form submission
        pdfFile = file;

        try {
            // Show preview section
            if (pdfPreviewSection) {
                pdfPreviewSection.classList.remove('hidden');
            }

            // Load PDF document
            const arrayBuffer = await file.arrayBuffer();
            pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

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
            showError(window.FAILED_TO_LOAD_PDF || 'Failed to load PDF file. Please try again.');
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

        // Clear preview container
        if (pdfPreviewContainer) {
            pdfPreviewContainer.innerHTML = '';
        }

        // Remove all drag handlers
        dragHandlers.forEach((handlers, card) => {
            handlers.forEach(({ event, handler }) => {
                card.removeEventListener(event, handler);
            });
        });
        dragHandlers.clear();

        // Reset state
        pageOrder = [];
        draggedElement = null;
    }

    function showError(message) {
        // Try to use a more user-friendly error display if available
        const errorContainer = document.getElementById('errorMessage');
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.classList.remove('hidden');
            setTimeout(() => {
                errorContainer.classList.add('hidden');
            }, 5000);
        } else {
            // Fallback to alert
            alert(message);
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
        const cards = pdfPreviewContainer.querySelectorAll('.pdf-page-card');

        cards.forEach(card => {
            // Skip if handlers already attached
            if (dragHandlers.has(card)) {
                return;
            }

            const handlers = [];

            const dragStartHandler = (e) => {
                draggedElement = card;
                card.style.opacity = '0.5';
                e.dataTransfer.effectAllowed = 'move';
            };

            const dragEndHandler = () => {
                if (draggedElement) {
                    draggedElement.style.opacity = '1';
                }
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

    function updateOrderFromPreview() {
        const cards = Array.from(pdfPreviewContainer.querySelectorAll('.pdf-page-card'));
        const newOrder = cards.map(card => parseInt(card.dataset.pageIndex));

        // Update pageOrder
        pageOrder = newOrder;

        // Update display indices and numbers
        cards.forEach((card, index) => {
            card.dataset.displayIndex = index;
            const numberBadge = card.querySelector('.absolute .bg-blue-600');
            if (numberBadge) {
                numberBadge.textContent = index + 1;
            }
        });
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!pdfFile || !pdfDoc) {
            showError(window.SELECT_PDF_FIRST || 'Please select a PDF file first.');
            return;
        }

        // Get API URL
        const apiUrl = window.API_URL || form.action || '/api/pdf-organize/organize/';

        // Create FormData
        const formData = new FormData();
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken.value);
        }

        // Use file from fileInput if available, otherwise use stored pdfFile
        const fileToSubmit = (fileInput && fileInput.files && fileInput.files.length > 0)
            ? fileInput.files[0]
            : pdfFile;

        if (!fileToSubmit) {
            showError(window.SELECT_PDF_FIRST || 'Please select a PDF file first.');
            return;
        }

        formData.append('pdf_file', fileToSubmit);
        formData.append('operation', 'reorder');

        // Add page order as JSON string (0-based indices)
        formData.append('page_order', JSON.stringify(pageOrder));

        // Show loading
        if (editButton) {
            editButton.disabled = true;
            const buttonText = editButton.querySelector('span span') || editButton;
            const originalText = buttonText.textContent;
            buttonText.textContent = window.ORGANIZING || 'Organizing...';
            buttonText.dataset.originalText = originalText;
        }

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || errorData.message || `Server error: ${response.status}`);
            }

            const blob = await response.blob();
            const outputFileName = pdfFile.name.replace(/\.pdf$/i, '_organized.pdf');

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

            // Fallback: direct download
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = outputFileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

        } catch (error) {
            const failedMsg = window.FAILED_TO_ORGANIZE || 'Failed to organize PDF';
            showError(`${failedMsg}: ${error.message || 'Unknown error'}`);
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error organizing PDF:', error);
            }
        } finally {
            // Restore button
            if (editButton) {
                editButton.disabled = false;
                const buttonText = editButton.querySelector('span span') || editButton;
                if (buttonText.dataset.originalText) {
                    buttonText.textContent = buttonText.dataset.originalText;
                }
            }
        }
    });
});
