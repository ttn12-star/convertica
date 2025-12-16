/**
 * JPG to PDF Multi-File Converter Component
 * Handles multiple image file selection, display, and conversion
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('converterForm');
    if (!form) return;

    const fileInput = document.getElementById('fileInput');
    const fileInputDrop = document.getElementById('fileInputDrop');
    const selectFileButton = document.getElementById('selectFileButton');
    const addMoreFilesButton = document.getElementById('addMoreFilesButton');
    const selectedFilesContainer = document.getElementById('selectedFilesContainer');
    const selectedFilesList = document.getElementById('selectedFilesList');
    const fileCount = document.getElementById('fileCount');
    const convertButton = document.getElementById('convertButton');
    const dropZone = document.getElementById('dropZone');
    const resultContainer = document.getElementById('converterResult');

    // Store selected files
    let selectedFiles = [];

    // Use event delegation for remove buttons (more reliable than onclick with index)
    if (selectedFilesList) {
        selectedFilesList.addEventListener('click', (e) => {
            const removeBtn = e.target.closest('button[data-file-index]');
            if (removeBtn) {
                e.preventDefault();
                e.stopPropagation();
                const index = parseInt(removeBtn.dataset.fileIndex, 10);
                if (!isNaN(index)) {
                    removeFile(index);
                }
            }
        });
    }

    // Create loading animation container
    const loadingContainer = document.createElement('div');
    loadingContainer.id = 'loadingContainer';
    loadingContainer.className = 'hidden mt-6';

    // Create download button container
    const downloadContainer = document.createElement('div');
    downloadContainer.id = 'downloadContainer';
    downloadContainer.className = 'hidden mt-6';

    // File input change handlers
    function handleFileSelection(files) {
        if (!files || files.length === 0) return;

        // Add new files to the list (avoid duplicates by name and size)
        Array.from(files).forEach(file => {
            // Check if file already exists
            const exists = selectedFiles.some(f =>
                f.name === file.name && f.size === file.size
            );

            if (!exists) {
                selectedFiles.push(file);
            }
        });

        updateFileList();
        updateConvertButton();
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            handleFileSelection(e.target.files);
        });
    }

    if (fileInputDrop) {
        fileInputDrop.addEventListener('change', (e) => {
            handleFileSelection(e.target.files);
        });
    }

    if (selectFileButton) {
        selectFileButton.addEventListener('click', () => {
            fileInput?.click();
        });
    }

    if (addMoreFilesButton) {
        addMoreFilesButton.addEventListener('click', () => {
            fileInput?.click();
        });
    }

    // Drag and drop handlers
    if (dropZone) {
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
            const files = e.dataTransfer.files;
            handleFileSelection(files);
        }, false);
    }

    // Remove file from list by index
    function removeFile(index) {
        if (index < 0 || index >= selectedFiles.length) {
            return;
        }
        selectedFiles.splice(index, 1);
        updateFileList();
        updateConvertButton();
    }

    // Update file list display
    function updateFileList() {
        if (!selectedFilesList) return;

        fileCount.textContent = selectedFiles.length;

        if (selectedFiles.length === 0) {
            selectedFilesContainer.classList.add('hidden');
            return;
        }

        selectedFilesContainer.classList.remove('hidden');

        selectedFilesList.innerHTML = selectedFiles.map((file, index) => {
            const fileSize = formatFileSize(file.size);
            return `
                <div class="flex items-center justify-between p-2.5 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors group">
                    <div class="flex items-center space-x-3 flex-1 min-w-0">
                        <svg class="w-5 h-5 text-pink-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                        </svg>
                        <div class="flex-1 min-w-0">
                            <p class="font-medium text-gray-900 text-sm truncate" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</p>
                            <p class="text-gray-500 text-xs">${fileSize}</p>
                        </div>
                    </div>
                    <button type="button"
                            class="ml-3 p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100"
                            data-file-index="${index}"
                            onclick="removeFileAtIndex(${index})"
                            aria-label="Remove file">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            `;
        }).join('');
    }

    // Make removeFileAtIndex available globally for onclick handlers
    window.removeFileAtIndex = function(index) {
        removeFile(index);
    };

    // Use functions from utils.js
    const formatFileSize = window.formatFileSize || function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };
    const escapeHtml = window.escapeHtml || function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    // Update convert button state
    function updateConvertButton() {
        if (convertButton) {
            convertButton.disabled = selectedFiles.length === 0;
        }
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (selectedFiles.length === 0) {
            showError(window.SELECT_FILE_MESSAGE || 'Please select at least one image file');
            return;
        }

        // Hide previous results
        hideResult();
        hideDownload();

        // Show loading animation
        window.showLoading('loadingContainer');

        // Disable form
        setFormDisabled(true);

        // Create FormData with all files
        const formData = new FormData();
        const fieldName = window.FILE_INPUT_NAME || 'image_file';

        // Append all files with the same field name
        selectedFiles.forEach(file => {
            formData.append(fieldName, file);
        });

        try {
            const response = await fetch(window.API_URL, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN || ''
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || window.ERROR_MESSAGE || 'Conversion failed');
            }

            const blob = await response.blob();

            // Hide loading, show download button
            window.hideLoading('loadingContainer');
            // Ensure download container exists
            if (!downloadContainer.parentNode && form.parentNode) {
                form.parentNode.insertBefore(downloadContainer, form.nextSibling);
            }

            window.showDownloadButton(blob, generateDownloadName(), 'downloadContainer', {
                successTitle: window.SUCCESS_TITLE || 'Conversion Complete!',
                successMessage: window.SUCCESS_MESSAGE || 'Your PDF is ready to download',
                downloadButtonText: window.DOWNLOAD_BUTTON_TEXT || 'Download PDF',
                convertAnotherText: window.CONVERT_ANOTHER_TEXT || 'Convert another file',
                onConvertAnother: () => {
                    selectedFiles = [];
                    updateFileList();
                    updateConvertButton();

                    if (fileInput) fileInput.value = '';
                    if (fileInputDrop) fileInputDrop.value = '';

                    hideDownload();
                    hideResult();
                    setFormDisabled(false);

                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });

                    setTimeout(() => {
                        if (selectFileButton) {
                            selectFileButton.focus({ preventScroll: true });
                        }
                    }, 800);
                }
            });

        } catch (err) {
            if (typeof console !== 'undefined' && console.error) {
                console.error('Conversion error:', err);
            }
            window.hideLoading('loadingContainer');
            window.showError(err.message, 'converterResult');
        } finally {
            setFormDisabled(false);
        }
    });

    // Generate download filename
    function generateDownloadName() {
        if (selectedFiles.length === 0) return 'converted.pdf';

        const firstFile = selectedFiles[0];
        let downloadName = firstFile.name;

        if (window.REPLACE_REGEX && window.REPLACE_TO) {
            try {
                const regex = new RegExp(window.REPLACE_REGEX, 'i');
                downloadName = firstFile.name.replace(regex, window.REPLACE_TO);

                // If multiple files, modify the name
                if (selectedFiles.length > 1) {
                    const base = downloadName.replace(/\.pdf$/i, '');
                    downloadName = `${base}_and_${selectedFiles.length - 1}_more.pdf`;
                }
            } catch (e) {
                console.warn('Invalid regex pattern:', window.REPLACE_REGEX);
            }
        }

        return downloadName;
    }

    function hideDownload() {
        window.hideDownload('downloadContainer');
    }

    function hideResult() {
        if (resultContainer) {
            resultContainer.classList.add('hidden');
        }
    }

    function setFormDisabled(disabled) {
        if (convertButton) {
            convertButton.disabled = disabled || selectedFiles.length === 0;
            if (disabled) {
                convertButton.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                convertButton.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
        if (fileInput) {
            fileInput.disabled = disabled;
        }
        if (fileInputDrop) {
            fileInputDrop.disabled = disabled;
        }
    }
});
