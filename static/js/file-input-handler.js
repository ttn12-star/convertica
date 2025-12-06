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
    const convertButton = document.getElementById('convertButton');
    
    if (!fileInput || !dropZone) return;

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
        
        // Enable convert button
        if (convertButton) {
            convertButton.disabled = false;
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
        
        // Disable convert button
        if (convertButton) {
            convertButton.disabled = true;
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
    if (selectFileButton) {
        selectFileButton.addEventListener('click', (e) => {
            e.preventDefault();
            if (fileInput) {
                fileInput.click();
            }
        });
    }

    // File input change (from button)
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                syncFileInputs(fileInput, fileInputDrop);
                showSelectedFile(e.target.files[0]);
            }
        });
    }

    // File input change (from drop zone)
    if (fileInputDrop) {
        fileInputDrop.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                syncFileInputs(fileInputDrop, fileInput);
                showSelectedFile(e.target.files[0]);
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

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('border-blue-500', 'bg-blue-100');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('border-blue-500', 'bg-blue-100');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files && files.length > 0) {
            // Create a new FileList-like object
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(files[0]);
            
            // Set files to both inputs
            if (fileInput) {
                fileInput.files = dataTransfer.files;
            }
            if (fileInputDrop) {
                fileInputDrop.files = dataTransfer.files;
            }
            
            showSelectedFile(files[0]);
            
            // Trigger change event
            if (fileInput) {
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        }
    }, false);

    // Click on drop zone to browse
    dropZone.addEventListener('click', () => {
        if (fileInputDrop) {
            fileInputDrop.click();
        }
    });
});
