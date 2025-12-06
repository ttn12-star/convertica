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
    
    // File input handlers
    selectPdfFilesButton?.addEventListener('click', () => {
        pdfFilesInput?.click();
    });
    
    addMorePdfFilesButton?.addEventListener('click', () => {
        pdfFilesInput?.click();
    });
    
    pdfFilesInput?.addEventListener('change', (e) => {
        handleFileSelection(e.target.files);
        e.target.value = ''; // Reset input
    });
    
    function handleFileSelection(files) {
        if (!files || files.length === 0) return;
        
        // Add new files to the list (avoid duplicates by name and size)
        Array.from(files).forEach(file => {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                alert(`File "${file.name}" is not a PDF file. Skipping.`);
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
            alert('Maximum 10 files allowed. Only the first 10 files will be used.');
        }
        
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
        
        // Add remove button handlers
        selectedPdfFilesList.querySelectorAll('.remove-file-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const fileId = e.currentTarget.dataset.fileId;
                removeFile(fileId);
            });
        });
        
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
        // Find and cleanup file data
        const fileData = selectedFiles.find(f => f.id === fileId);
        if (fileData) {
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
        }
        
        selectedFiles = selectedFiles.filter(f => f.id !== fileId);
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
            canvasContainer.innerHTML = '<p class="text-xs text-red-600">Error loading preview</p>';
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
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Form submission - intercept and use API
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (selectedFiles.length < 2) {
            alert('Please select at least 2 PDF files to merge.');
            return;
        }
        
        if (selectedFiles.length > 10) {
            alert('Maximum 10 PDF files allowed.');
            return;
        }
        
        // Get API URL from window.API_URL or form action
        const apiUrl = window.API_URL || form.action || '/api/pdf-organize/merge/';
        
        // Create FormData with files in order
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        
        selectedFiles.forEach((fileData) => {
            formData.append('pdf_files', fileData.file);
        });
        
        formData.append('order', 'upload'); // Order is determined by array order
        
        // Show loading
        if (editButton) {
            editButton.disabled = true;
            const buttonText = editButton.querySelector('span span');
            if (buttonText) {
                const originalText = buttonText.textContent;
                buttonText.textContent = 'Merging...';
                buttonText.dataset.originalText = originalText;
            } else {
                editButton.textContent = 'Merging...';
            }
        }
        
        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                // Get filename from Content-Disposition header
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'merged.pdf';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }
                
                // Download file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                // Show success message
                alert('PDFs merged successfully!');
            } else {
                const errorData = await response.json().catch(() => ({}));
                alert(errorData.error || 'Failed to merge PDFs. Please try again.');
            }
        } catch (error) {
            console.error('Error merging PDFs:', error);
            alert('An error occurred while merging PDFs. Please try again.');
        } finally {
            if (editButton) {
                editButton.disabled = false;
                const buttonText = editButton.querySelector('span span');
                if (buttonText && buttonText.dataset.originalText) {
                    buttonText.textContent = buttonText.dataset.originalText;
                }
            }
        }
    });
    
    // Initialize
    updateButtons();
});

