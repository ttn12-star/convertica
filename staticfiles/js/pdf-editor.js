/**
 * PDF Editor Component
 * Handles PDF editing with loading animation and download button
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('editorForm');
    if (!form) return;

    const fileInput = document.getElementById('fileInput');
    const fileInputDrop = document.getElementById('fileInputDrop');
    const submitButton = form.querySelector('button[type="submit"]');
    const resultContainer = document.getElementById('editorResult');

    // Create loading animation container
    const loadingContainer = document.getElementById('loadingContainer');
    if (!loadingContainer) {
        const newContainer = document.createElement('div');
        newContainer.id = 'loadingContainer';
        newContainer.className = 'hidden mt-6';
        form.parentNode.insertBefore(newContainer, form.nextSibling);
    }

    // Create download button container
    const downloadContainer = document.getElementById('downloadContainer');
    if (!downloadContainer) {
        const newContainer = document.createElement('div');
        newContainer.id = 'downloadContainer';
        newContainer.className = 'hidden mt-6';
        form.parentNode.insertBefore(newContainer, form.nextSibling);
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Check if this is a merge operation handled by merge-pdf-multi.js
        // If pdf_files_input exists and merge-pdf-multi.js is handling it, skip this handler
        const pdfFilesInput = document.getElementById('pdf_files_input');
        const selectedPdfFilesList = document.getElementById('selectedPdfFilesList');
        if (pdfFilesInput && selectedPdfFilesList) {
            // This is merge page, let merge-pdf-multi.js handle it
            return;
        }

        const formData = new FormData();
        const singleFieldName = window.FILE_INPUT_NAME || 'pdf_file';

        const selectedFiles = (fileInput?.files && fileInput.files.length > 0)
            ? fileInput.files
            : (fileInputDrop?.files && fileInputDrop.files.length > 0)
                ? fileInputDrop.files
                : null;

        const isBatchMode = Boolean(
            window.BATCH_ENABLED &&
            window.IS_PREMIUM &&
            selectedFiles &&
            selectedFiles.length > 1 &&
            window.BATCH_API_URL &&
            window.BATCH_FIELD_NAME
        );

        let selectedFile = selectedFiles?.[0] || null;
        if (!selectedFile) {
            showError(window.SELECT_FILE_MESSAGE || 'Please select a file');
            return;
        }

        if (isBatchMode) {
            const batchFieldName = window.BATCH_FIELD_NAME;
            Array.from(selectedFiles).forEach((f) => {
                formData.append(batchFieldName, f);
            });
        } else {
            formData.append(singleFieldName, selectedFile);
        }

        // Hide previous results
        hideResult();
        hideDownload();

        // Show loading animation (disable progress bar for batch mode)
        window.showLoading('loadingContainer', { showProgress: !isBatchMode });

        // Disable form
        setFormDisabled(true);

        // Set cancel callback so the cancel button can restore the form
        window._onCancelCallback = () => {
            window.hideLoading('loadingContainer');
            setFormDisabled(false);
        };

        // Create AbortController for cancel support
        const abortController = new AbortController();
        window._currentAbortController = abortController;

        // Collect all form fields (except file and CSRF token)
        const formElements = form.querySelectorAll('input, select, textarea');
        formElements.forEach(element => {
            if (element.type === 'file' || element.name === 'csrfmiddlewaretoken') {
                return;
            }

            // Skip hidden watermark fields if not selected
            if (element.name === 'watermark_file' && document.getElementById('watermarkTypeText')?.checked) {
                return;
            }
            if (element.name === 'watermark_text' && document.getElementById('watermarkTypeImage')?.checked) {
                return;
            }

            if (element.value && element.value.trim() !== '') {
                // Convert number inputs to proper types
                if (element.type === 'number') {
                    const numValue = parseFloat(element.value);
                    if (!isNaN(numValue)) {
                        formData.append(element.name, numValue);
                    }
                } else {
                    formData.append(element.name, element.value);
                }
            }
        });

        try {
            const apiUrl = isBatchMode ? window.BATCH_API_URL : window.API_URL;
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN
                },
                body: formData,
                signal: abortController.signal,
            });

            const blob = await response.blob();

            if (!response.ok) {
                // Try to parse error message
                try {
                    const errorData = await blob.text();
                    const errorJson = JSON.parse(errorData);
                    throw new Error(errorJson.error || window.ERROR_MESSAGE);
                } catch {
                    throw new Error(window.ERROR_MESSAGE || 'Editing failed');
                }
            }

            // Success - show download button
            window.hideLoading('loadingContainer');

            // Check if this is a compression response
            const inputSize = response.headers.get('X-Input-Size');
            const outputSize = response.headers.get('X-Output-Size');
            const compressionRatio = response.headers.get('X-Compression-Ratio');

            if (inputSize && outputSize && compressionRatio) {
                // This is a compression response - show compression notification
                showCompressionNotification(
                    parseInt(inputSize),
                    parseInt(outputSize),
                    parseFloat(compressionRatio)
                );
            }

            // Determine filename
            const contentDisposition = response.headers.get('content-disposition');
            let downloadName = isBatchMode ? 'convertica.zip' : selectedFile.name;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    downloadName = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            window.showDownloadButton(blob, downloadName, 'downloadContainer', {
                successTitle: window.SUCCESS_TITLE || 'Editing Complete!',
                downloadButtonText: window.DOWNLOAD_BUTTON_TEXT || 'Download File',
                convertAnotherText: window.EDIT_ANOTHER_TEXT || 'Edit another file',
                onConvertAnother: () => {
                    const fileInput = document.getElementById('fileInput');
                    const fileInputDrop = document.getElementById('fileInputDrop');
                    const selectedFileDiv = document.getElementById('selectedFile');
                    const fileInfo = document.getElementById('fileInfo');
                    const editButton = document.getElementById('editButton');

                    if (fileInput) fileInput.value = '';
                    if (fileInputDrop) fileInputDrop.value = '';

                    if (selectedFileDiv) {
                        selectedFileDiv.classList.add('hidden');
                    }
                    if (fileInfo) {
                        fileInfo.classList.remove('hidden');
                    }

                    if (editButton) {
                        editButton.disabled = true;
                    }

                    hideDownload();
                    hideResult();
                    setFormDisabled(false);

                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });

                    setTimeout(() => {
                        const selectFileButton = document.getElementById('selectFileButton');
                        if (selectFileButton) {
                            selectFileButton.focus({ preventScroll: true });
                        }
                    }, 800);
                }
            });
            setFormDisabled(false);

        } catch (error) {
            if (error && error.name === 'AbortError') {
                // User cancelled — UI already cleaned up by cancelCurrentOperation
                return;
            }
            window.hideLoading('loadingContainer');
            window.showError(error.message || window.ERROR_MESSAGE, 'editorResult');
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
        if (submitButton) {
            submitButton.disabled = disabled;
        }
        const inputs = form.querySelectorAll('input, select, textarea, button');
        inputs.forEach(input => {
            if (input !== submitButton) {
                input.disabled = disabled;
            }
        });
    }

    // Use formatFileSize from utils.js
    const formatFileSize = window.formatFileSize || function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };

    function showCompressionNotification(inputSize, outputSize, compressionRatio) {
        // Create notification container if it doesn't exist
        let notificationContainer = document.getElementById('compressionNotification');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'compressionNotification';
            notificationContainer.className = 'mt-4';
            const form = document.getElementById('editorForm');
            if (form && form.parentNode) {
                form.parentNode.insertBefore(notificationContainer, form.nextSibling);
            }
        }

        const inputSizeFormatted = formatFileSize(inputSize);
        const outputSizeFormatted = formatFileSize(outputSize);
        const savedSize = inputSize - outputSize;
        const savedSizeFormatted = formatFileSize(savedSize);

        // Determine color based on compression ratio
        let bgColor = 'from-blue-50 to-blue-100';
        let borderColor = 'border-blue-300';
        let textColor = 'text-blue-900';
        let iconColor = 'text-blue-600';

        if (compressionRatio > 30) {
            bgColor = 'from-green-50 to-green-100';
            borderColor = 'border-green-300';
            textColor = 'text-green-900';
            iconColor = 'text-green-600';
        } else if (compressionRatio > 10) {
            bgColor = 'from-yellow-50 to-yellow-100';
            borderColor = 'border-yellow-300';
            textColor = 'text-yellow-900';
            iconColor = 'text-yellow-600';
        }

        notificationContainer.innerHTML = `
            <div class="bg-gradient-to-br ${bgColor} border-2 ${borderColor} rounded-xl p-5 sm:p-6 animate-fade-in">
                <div class="flex items-start space-x-4">
                    <div class="flex-shrink-0">
                        <div class="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm">
                            <svg class="w-6 h-6 ${iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                            </svg>
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h4 class="text-lg font-bold ${textColor} mb-2">
                            ${compressionRatio > 0 ? '✓ File Compressed Successfully!' : 'File Processed'}
                        </h4>
                        <div class="space-y-2 text-sm ${textColor}">
                            <div class="flex items-center justify-between">
                                <span class="font-medium">Original Size:</span>
                                <span class="font-mono">${inputSizeFormatted}</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="font-medium">Compressed Size:</span>
                                <span class="font-mono font-bold">${outputSizeFormatted}</span>
                            </div>
                            <div class="flex items-center justify-between pt-2 border-t ${borderColor}">
                                <span class="font-bold">Size Reduction:</span>
                                <span class="font-mono font-bold">${compressionRatio.toFixed(1)}% (${savedSizeFormatted})</span>
                            </div>
                        </div>
                    </div>
                    <button onclick="this.parentElement.parentElement.remove()"
                            class="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        notificationContainer.classList.remove('hidden');

        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (notificationContainer && notificationContainer.parentNode) {
                notificationContainer.classList.add('hidden');
            }
        }, 10000);
    }
});
