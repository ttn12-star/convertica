/**
 * Merge PDF Multi-File Component
 * Handles multiple PDF file selection, preview, reordering, and merging
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('editorForm') || document.getElementById('converterForm');
    if (!form) return;

    const pdfFilesInput = document.getElementById('pdf_files_input');
    const selectPdfFilesButton = document.getElementById('selectPdfFilesButton');
    const addMorePdfFilesButton = document.getElementById('addMorePdfFilesButton');
    const mergeDropZone = document.getElementById('mergeDropZone');
    const selectedPdfFilesContainer = document.getElementById('selectedPdfFilesContainer');
    const selectedPdfFilesList = document.getElementById('selectedPdfFilesList');
    const pdfFileCount = document.getElementById('pdfFileCount');
    const pdfPreviewSection = document.getElementById('pdfPreviewSection');
    const pdfPreviewContainer = document.getElementById('pdfPreviewContainer');
    const editButton = document.getElementById('editButton');

    // Store selected files with metadata
    let selectedFiles = [];
    let draggedElement = null;

    // Initialize PDF.js worker
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

    // Use event delegation for remove buttons (more reliable)
    if (selectedPdfFilesList) {
        selectedPdfFilesList.addEventListener('click', (e) => {
            const removeBtn = e.target.closest('.remove-file-btn');
            if (removeBtn) {
                e.preventDefault();
                e.stopPropagation();
                const fileId = removeBtn.dataset.fileId || removeBtn.getAttribute('data-file-id');
                if (fileId) {
                    removeFile(fileId);
                }
            }
        });
    }

    // File input handlers
    selectPdfFilesButton?.addEventListener('click', () => {
        pdfFilesInput?.click();
    });

    addMorePdfFilesButton?.addEventListener('click', () => {
        pdfFilesInput?.click();
    });

    pdfFilesInput?.addEventListener('change', async (e) => {
        // Small delay for mobile devices
        await new Promise(resolve => setTimeout(resolve, 50));
        handleFileSelection(e.target.files);
        e.target.value = ''; // Reset input
    });

    // Drag & drop support for merge page
    if (mergeDropZone) {
        // Local helpers to prevent default browser behavior
        const preventDefaults = (e) => {
            e.preventDefault();
            e.stopPropagation();
        };

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            mergeDropZone.addEventListener(eventName, preventDefaults, false);
        });

        let dragCounter = 0;

        mergeDropZone.addEventListener('dragenter', () => {
            dragCounter++;
            mergeDropZone.classList.add('border-blue-500', 'bg-blue-100', 'border-4');
            mergeDropZone.classList.remove('border-2', 'border-gray-300', 'bg-gray-50');
        });

        mergeDropZone.addEventListener('dragover', () => {
            mergeDropZone.classList.add('border-blue-500', 'bg-blue-100', 'border-4');
            mergeDropZone.classList.remove('border-2', 'border-gray-300', 'bg-gray-50');
        });

        mergeDropZone.addEventListener('dragleave', () => {
            dragCounter--;
            if (dragCounter <= 0) {
                dragCounter = 0;
                mergeDropZone.classList.remove('border-blue-500', 'bg-blue-100', 'border-4');
                mergeDropZone.classList.add('border-2', 'border-gray-300', 'bg-gray-50');
            }
        });

        mergeDropZone.addEventListener('drop', (e) => {
            dragCounter = 0;
            mergeDropZone.classList.remove('border-blue-500', 'bg-blue-100', 'border-4');
            mergeDropZone.classList.add('border-2', 'border-gray-300', 'bg-gray-50');

            const dt = e.dataTransfer;
            const files = dt?.files;
            if (files && files.length > 0) {
                handleFileSelection(files);
            }
        });

        // Также принимаем дроп на всю форму, чтобы не было случайных промахов мимо зоны
        if (form) {
            ['dragover', 'drop'].forEach(eventName => {
                form.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                });
            });

            form.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt?.files;
                if (files && files.length > 0) {
                    handleFileSelection(files);
                }
            });
        }
    }

    function handleFileSelection(files) {
        if (!files || files.length === 0) return;

        console.log('handleFileSelection called with files:', files);
        console.log('Before selection - selectedFiles.length:', selectedFiles.length);

        // Add new files to the list (avoid duplicates by name and size)
        Array.from(files).forEach(file => {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                const notPdfMsg = window.FILE_NOT_PDF || 'is not a PDF file. Skipping.';
                alert(`"${file.name}" ${notPdfMsg}`);
                return;
            }

            // Check if file already exists
            const exists = selectedFiles.some(f =>
                f.name === file.name && f.size === file.size
            );

            if (!exists) {
                selectedFiles.push({
                    file: file,
                    id: Date.now() + Math.random(),
                    preview: null
                });
            }
        });

        // Limit to 10 files
        if (selectedFiles.length > 10) {
            selectedFiles = selectedFiles.slice(0, 10);
            alert(window.MAX_FILES_EXCEEDED || 'Maximum 10 files allowed. Only the first 10 files will be used.');
        }

        console.log('After selection - selectedFiles.length:', selectedFiles.length);

        updateFileList();
        updatePreview();
        updateButtons();
    }

    function updateFileList() {
        if (!selectedPdfFilesList) return;

        selectedPdfFilesList.innerHTML = '';

        selectedFiles.forEach((fileData, index) => {
            const file = fileData.file;
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);

            const fileItem = document.createElement('div');
            fileItem.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200';
            fileItem.dataset.fileId = fileData.id;
            fileItem.innerHTML = `
                <div class="flex items-center space-x-3 flex-1 min-w-0">
                    <div class="flex-shrink-0 w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                        <span class="text-xs font-bold text-blue-600">${index + 1}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-900 truncate">${escapeHtml(file.name)}</p>
                        <p class="text-xs text-gray-500">${sizeMB} MB</p>
                    </div>
                </div>
                <button type="button"
                        class="remove-file-btn ml-3 p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors flex-shrink-0"
                        data-file-id="${fileData.id}"
                        aria-label="Remove file">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            `;

            selectedPdfFilesList.appendChild(fileItem);
        });

        // Remove button handlers are handled via event delegation set up at initialization
        // No need to attach individual handlers here

        // Update count
        if (pdfFileCount) {
            pdfFileCount.textContent = selectedFiles.length;
        }

        // Show/hide container
        if (selectedPdfFilesContainer) {
            if (selectedFiles.length > 0) {
                selectedPdfFilesContainer.classList.remove('hidden');
            } else {
                selectedPdfFilesContainer.classList.add('hidden');
            }
        }
    }

    function removeFile(fileId) {
        // Convert fileId to number for comparison (data attributes are strings)
        // ID is created as Date.now() + Math.random(), so it's a number
        const fileIdNum = typeof fileId === 'string' ? parseFloat(fileId) : fileId;

        // Find and cleanup file data - use loose comparison to handle string/number mismatch
        const fileData = selectedFiles.find(f => {
            // Compare as numbers (with tolerance for floating point)
            if (Math.abs(f.id - fileIdNum) < 0.0001) return true;
            // Compare as strings
            if (f.id.toString() === fileId.toString()) return true;
            // Direct comparison
            if (f.id === fileIdNum || f.id === fileId) return true;
            return false;
        });

        if (!fileData) {
            return;
        }

        // Cleanup PDF document if exists
        if (fileData.pdfDoc) {
            try {
                fileData.pdfDoc.destroy();
            } catch (e) {
                // Ignore cleanup errors
            }
        }
        // Cleanup preview canvas
        if (fileData.preview) {
            const ctx = fileData.preview.getContext('2d');
            ctx.clearRect(0, 0, fileData.preview.width, fileData.preview.height);
        }

        // Remove preview card from DOM - try multiple selectors
        const previewCard = pdfPreviewContainer?.querySelector(`[data-file-id="${fileData.id}"]`) ||
                          pdfPreviewContainer?.querySelector(`[data-file-id="${fileId}"]`) ||
                          pdfPreviewContainer?.querySelector(`[data-file-id="${fileIdNum}"]`);
        if (previewCard) {
            previewCard.remove();
        }

        // Remove from array - use the same comparison logic
        selectedFiles = selectedFiles.filter(f => {
            // Keep files that don't match
            if (Math.abs(f.id - fileIdNum) < 0.0001) return false;
            if (f.id.toString() === fileId.toString()) return false;
            if (f.id === fileIdNum || f.id === fileId) return false;
            return true;
        });

        updateFileList();
        updatePreview();
        updateButtons();
    }

    async function updatePreview() {
        if (!pdfPreviewContainer) return;

        pdfPreviewContainer.innerHTML = '';

        if (selectedFiles.length === 0) {
            if (pdfPreviewSection) {
                pdfPreviewSection.classList.add('hidden');
            }
            return;
        }

        if (pdfPreviewSection) {
            pdfPreviewSection.classList.remove('hidden');
        }

        // Generate previews for each file
        for (let i = 0; i < selectedFiles.length; i++) {
            const fileData = selectedFiles[i];
            await generatePreview(fileData, i);
        }

        // Make previews sortable
        makeSortable();
    }

    async function generatePreview(fileData, index) {
        const previewCard = document.createElement('div');
        previewCard.className = 'pdf-preview-card bg-white rounded-lg border-2 border-gray-200 p-2 cursor-move hover:border-blue-400 transition-colors';
        previewCard.dataset.fileId = fileData.id;
        previewCard.dataset.index = index;
        previewCard.draggable = true;

        previewCard.innerHTML = `
            <div class="relative">
                <div class="w-full aspect-[3/4] bg-gray-100 rounded border border-gray-200 flex items-center justify-center overflow-hidden">
                    <div class="pdf-preview-canvas-container text-center">
                        <div class="spinner-border text-blue-600" role="status">
                            <span class="sr-only">Loading...</span>
                        </div>
                    </div>
                </div>
                <div class="absolute top-2 left-2 bg-blue-600 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
                    ${index + 1}
                </div>
            </div>
            <p class="text-xs text-gray-600 mt-2 truncate" title="${escapeHtml(fileData.file.name)}">
                ${escapeHtml(fileData.file.name)}
            </p>
        `;

        pdfPreviewContainer.appendChild(previewCard);

        // Load PDF and render first page
        let pdf = null;
        try {
            const arrayBuffer = await fileData.file.arrayBuffer();
            pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            const page = await pdf.getPage(1);
            const viewport = page.getViewport({ scale: 0.5 });

            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const context = canvas.getContext('2d');

            await page.render({
                canvasContext: context,
                viewport: viewport
            }).promise;

            const canvasContainer = previewCard.querySelector('.pdf-preview-canvas-container');
            canvasContainer.innerHTML = '';
            canvasContainer.appendChild(canvas);

            fileData.preview = canvas;
            fileData.pdfDoc = pdf; // Store for cleanup
        } catch (error) {
            if (typeof console !== 'undefined' && console.error) {
                console.error('Error loading PDF preview:', error);
            }
            const canvasContainer = previewCard.querySelector('.pdf-preview-canvas-container');
            canvasContainer.innerHTML = `<p class="text-xs text-red-600">${window.ERROR_LOADING_PREVIEW || 'Error loading preview'}</p>`;
            // Cleanup on error
            if (pdf) {
                try {
                    pdf.destroy();
                } catch (e) {
                    // Ignore cleanup errors
                }
            }
        }
    }

    function makeSortable() {
        const cards = pdfPreviewContainer.querySelectorAll('.pdf-preview-card');

        cards.forEach(card => {
            card.addEventListener('dragstart', (e) => {
                draggedElement = card;
                card.style.opacity = '0.5';
                e.dataTransfer.effectAllowed = 'move';
            });

            card.addEventListener('dragend', () => {
                card.style.opacity = '1';
                draggedElement = null;
            });

            card.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';

                if (draggedElement && draggedElement !== card) {
                    const rect = card.getBoundingClientRect();
                    const midY = rect.top + rect.height / 2;

                    if (e.clientY < midY) {
                        card.parentNode.insertBefore(draggedElement, card);
                    } else {
                        card.parentNode.insertBefore(draggedElement, card.nextSibling);
                    }
                }
            });

            card.addEventListener('drop', (e) => {
                e.preventDefault();
                updateOrderFromPreview();
            });
        });
    }

    function updateOrderFromPreview() {
        const cards = Array.from(pdfPreviewContainer.querySelectorAll('.pdf-preview-card'));
        const newOrder = cards.map(card => card.dataset.fileId);

        // Reorder selectedFiles array
        selectedFiles.sort((a, b) => {
            const indexA = newOrder.indexOf(a.id.toString());
            const indexB = newOrder.indexOf(b.id.toString());
            return indexA - indexB;
        });

        // Update preview with new order numbers
        cards.forEach((card, index) => {
            const numberBadge = card.querySelector('.absolute .bg-blue-600');
            if (numberBadge) {
                numberBadge.textContent = index + 1;
            }
            card.dataset.index = index;
        });

        // Update file list
        updateFileList();
    }

    function updateButtons() {
        const hasFiles = selectedFiles.length >= 2;

        if (editButton) {
            editButton.disabled = !hasFiles;
            if (hasFiles) {
                editButton.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                editButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }

        if (addMorePdfFilesButton) {
            if (selectedFiles.length > 0 && selectedFiles.length < 10) {
                addMorePdfFilesButton.classList.remove('hidden');
            } else {
                addMorePdfFilesButton.classList.add('hidden');
            }
        }
    }

    // Use escapeHtml from utils.js
    const escapeHtml = window.escapeHtml || function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    // Form submission - intercept and use API
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        e.stopPropagation(); // Prevent other handlers from running

        // Small delay to ensure files are processed on mobile
        await new Promise(resolve => setTimeout(resolve, 100));

        // Additional check - if no files in selectedFiles, check form input directly
        if (selectedFiles.length === 0 && pdfFilesInput && pdfFilesInput.files.length > 0) {
            console.log('Fallback: Processing files from input directly');
            handleFileSelection(pdfFilesInput.files);
            // Another small delay after processing
            await new Promise(resolve => setTimeout(resolve, 50));
        }

        console.log('Form submit - selectedFiles.length:', selectedFiles.length);
        console.log('Form submit - selectedFiles:', selectedFiles);

        if (selectedFiles.length < 2) {
            window.showError('Please select at least 2 PDF files to merge.', 'editorResult');
            return;
        }

        if (selectedFiles.length > 10) {
            window.showError('Maximum 10 PDF files allowed.', 'editorResult');
            return;
        }

        // Get API URL from window.API_URL or form action
        const apiUrl = window.API_URL || form.action || '/api/pdf-organize/merge/';

        // Create FormData with files in order
        const formData = new FormData();
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || window.CSRF_TOKEN;
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }

        // Append files in the order they appear in selectedFiles array
        // Use the same field name 'pdf_files' for all files so Django can get them with getlist()
        // Important: FormData.append with the same field name creates an array on the server
        // The order of append() calls determines the order in getlist()
        selectedFiles.forEach((fileData, index) => {
            const file = fileData.file;
            // Append file with explicit filename to ensure proper upload
            // Third parameter (filename) is optional but helps with server-side handling
            formData.append('pdf_files', file, file.name);
        });

        // Verify files are in FormData (for debugging)
        if (selectedFiles.length !== Array.from(formData.getAll('pdf_files')).length) {
            console.error('File count mismatch in FormData!');
        }

        formData.append('order', 'upload'); // Order is determined by array order

        // Hide previous results
        hideResult();
        hideDownload();

        // Show loading
        window.showLoading('loadingContainer');

        // Disable form
        setFormDisabled(true);

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const blob = await response.blob();

            if (!response.ok) {
                try {
                    const errorData = await blob.text();
                    const errorJson = JSON.parse(errorData);
                    throw new Error(errorJson.error || window.ERROR_MESSAGE || 'Failed to merge PDFs. Please try again.');
                } catch {
                    throw new Error(window.ERROR_MESSAGE || 'Failed to merge PDFs. Please try again.');
                }
            }

            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'merged.pdf';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            // Use first file name for output filename
            const originalFileName = selectedFiles[0]?.file?.name || 'merged';
            const replaceRegex = new RegExp(window.REPLACE_REGEX || '\\.pdf$', 'i');
            const replaceTo = window.REPLACE_TO || '_merged.pdf';
            const outputFileName = originalFileName.replace(replaceRegex, replaceTo);

            // Hide loading and show download button
            window.hideLoading('loadingContainer');
            window.showDownloadButton(blob, outputFileName, 'downloadContainer', {
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
                    // Hide preview section
                    const pdfPreviewSection = document.getElementById('pdfPreviewSection');
                    if (pdfPreviewSection) {
                        pdfPreviewSection.classList.add('hidden');
                    }
                    // Reset file list
                    selectedFiles = [];
                    updateFileList();
                    updateMergeButton();
                    hideDownload();
                    hideResult();
                    setFormDisabled(false);
                    // Scroll to top first, then focus
                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });
                    // Focus on the correct button for merge page
                    setTimeout(() => {
                        const selectPdfFilesButton = document.getElementById('selectPdfFilesButton');
                        if (selectPdfFilesButton) {
                            selectPdfFilesButton.focus({ preventScroll: true });
                        }
                    }, 800);
                }
            });
            setFormDisabled(false);

        } catch (error) {
            console.error('Error merging PDFs:', error);
            window.hideLoading('loadingContainer');
            window.showError(error.message || 'An error occurred while merging PDFs. Please try again.', 'editorResult');
            setFormDisabled(false);
        }
    });

    function hideDownload() {
        window.hideDownload('downloadContainer');
    }

    function hideResult() {
        const container = document.getElementById('editorResult');
        if (container) {
            container.classList.add('hidden');
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

    // Initialize
    updateButtons();
});
