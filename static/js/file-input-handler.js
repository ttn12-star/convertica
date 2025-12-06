/**
 * File Input Handler
 * Handles drag & drop, file selection display, and file removal
 */
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const fileInputDrop = document.getElementById('fileInputDrop');
    const selectFileButton = document.getElementById('selectFileButton');
    const dropZone = document.getElementById('dropZone');
    const selectedFileDiv = document.getElementById('selectedFile');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileInfo = document.getElementById('fileInfo');
    const removeFileBtn = document.getElementById('removeFile');
    // Try to find either convertButton (for converter pages) or editButton (for editor pages)
    const convertButton = document.getElementById('convertButton') || document.getElementById('editButton');
    
    // Only proceed if we have the essential elements
    if (!fileInput) return;
    // dropZone is optional (not all pages have it)

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Show selected file and enable convert button
    function showSelectedFile(file) {
        if (!selectedFileDiv || !fileName || !fileSize) return;
        
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        selectedFileDiv.classList.remove('hidden');
        if (fileInfo) {
            fileInfo.classList.add('hidden');
        }
        
        // Enable convert/edit button
        if (convertButton) {
            convertButton.disabled = false;
            convertButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }

    // Hide selected file and disable convert button
    function hideSelectedFile() {
        if (selectedFileDiv) {
            selectedFileDiv.classList.add('hidden');
        }
        if (fileInfo) {
            fileInfo.classList.remove('hidden');
        }
        if (fileInput) {
            fileInput.value = '';
        }
        if (fileInputDrop) {
            fileInputDrop.value = '';
        }
        
        // Disable convert/edit button
        if (convertButton) {
            convertButton.disabled = true;
            convertButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    // Sync files between two inputs
    function syncFileInputs(sourceInput, targetInput) {
        if (sourceInput.files && sourceInput.files.length > 0) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(sourceInput.files[0]);
            targetInput.files = dataTransfer.files;
        }
    }

    // Button click handler
    // Note: Don't preventDefault to allow other handlers to work
    if (selectFileButton && fileInput) {
        selectFileButton.addEventListener('click', (e) => {
            // Trigger file input click
            fileInput.click();
        });
    }

    // File input change (from button)
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                // Sync to fileInputDrop
                if (fileInputDrop) {
                    syncFileInputs(fileInput, fileInputDrop);
                }
                showSelectedFile(file);
                
                // Dispatch custom event for other scripts (like organize-pdf.js)
                const customEvent = new CustomEvent('fileSelected', {
                    detail: { file: file },
                    bubbles: true
                });
                document.dispatchEvent(customEvent);
            }
        });
    }

    // File input change (from drop zone)
    if (fileInputDrop) {
        fileInputDrop.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                // Sync to fileInput so pdf-crop-editor.js can pick it up
                if (fileInput) {
                    syncFileInputs(fileInputDrop, fileInput);
                    // Trigger change event on fileInput to ensure pdf-crop-editor.js handles it
                    // Use setTimeout to ensure sync happens first
                    setTimeout(() => {
                        if (fileInput.files && fileInput.files.length > 0) {
                            const changeEvent = new Event('change', { bubbles: true });
                            fileInput.dispatchEvent(changeEvent);
                        }
                    }, 0);
                }
                showSelectedFile(file);
                
                // Dispatch custom event for other scripts (like organize-pdf.js)
                const customEvent = new CustomEvent('fileSelected', {
                    detail: { file: file },
                    bubbles: true
                });
                document.dispatchEvent(customEvent);
            }
        });
    }

    // Remove file button
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            hideSelectedFile();
        });
    }

    // Drag and drop handlers (only if dropZone exists)
    if (dropZone) {
        let dragCounter = 0; // Track nested drag events
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        dropZone.addEventListener('dragenter', (e) => {
            dragCounter++;
            dropZone.classList.add('border-blue-500', 'bg-blue-100', 'border-4');
            dropZone.classList.remove('border-2', 'border-gray-300', 'bg-gray-50');
        }, false);

        dropZone.addEventListener('dragover', (e) => {
            // Keep highlighting during drag over
            dropZone.classList.add('border-blue-500', 'bg-blue-100', 'border-4');
            dropZone.classList.remove('border-2', 'border-gray-300', 'bg-gray-50');
        }, false);

        dropZone.addEventListener('dragleave', (e) => {
            dragCounter--;
            if (dragCounter === 0) {
                dropZone.classList.remove('border-blue-500', 'bg-blue-100', 'border-4');
                dropZone.classList.add('border-2', 'border-gray-300', 'bg-gray-50');
            }
        }, false);

        dropZone.addEventListener('drop', (e) => {
            dragCounter = 0;
            dropZone.classList.remove('border-blue-500', 'bg-blue-100', 'border-4');
            dropZone.classList.add('border-2', 'border-gray-300', 'bg-gray-50');
            
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files && files.length > 0) {
                // Create a new FileList-like object
                const dataTransfer = new DataTransfer();
                // Handle multiple files if needed (for jpg_to_pdf)
                if (files.length > 1 && fileInputDrop && fileInputDrop.hasAttribute('multiple')) {
                    for (let i = 0; i < files.length; i++) {
                        dataTransfer.items.add(files[i]);
                    }
                } else {
                    dataTransfer.items.add(files[0]);
                }
                
                // Set files to both inputs
                if (fileInput) {
                    fileInput.files = dataTransfer.files;
                }
                if (fileInputDrop) {
                    fileInputDrop.files = dataTransfer.files;
                }
                
                showSelectedFile(files[0]);
                
                // Trigger change event on both inputs to ensure all handlers pick it up
                if (fileInput) {
                    const event = new Event('change', { bubbles: true });
                    fileInput.dispatchEvent(event);
                }
                if (fileInputDrop) {
                    const event = new Event('change', { bubbles: true });
                    fileInputDrop.dispatchEvent(event);
                }
                
                // Dispatch custom event for other scripts (like organize-pdf.js)
                const customEvent = new CustomEvent('fileSelected', {
                    detail: { file: files[0] },
                    bubbles: true
                });
                document.dispatchEvent(customEvent);
            }
        }, false);

        // Remove click handler - drop zone is for drag & drop only
        // Users should use the "Select file" button to browse files
    }
});
