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
        const fieldName = window.FILE_INPUT_NAME || 'pdf_file';

        // Handle multiple files for merge (legacy support)
        let selectedFile = null;
        if (fieldName === 'pdf_files') {
            const pdfFilesInputLegacy = document.getElementById('pdf_files');
            if (!pdfFilesInputLegacy || !pdfFilesInputLegacy.files || pdfFilesInputLegacy.files.length === 0) {
                showError(window.SELECT_FILE_MESSAGE || 'Please select at least 2 PDF files');
                return;
            }
            if (pdfFilesInputLegacy.files.length < 2) {
                showError('Please select at least 2 PDF files to merge');
                return;
            }
            if (pdfFilesInputLegacy.files.length > 10) {
                showError('Maximum 10 PDF files allowed');
                return;
            }
            // Add all files to formData
            for (let i = 0; i < pdfFilesInputLegacy.files.length; i++) {
                formData.append('pdf_files', pdfFilesInputLegacy.files[i]);
            }
            selectedFile = pdfFilesInputLegacy.files[0]; // Use first file for display purposes
        } else {
            // Get file from either input for single file operations
            selectedFile = fileInput?.files?.[0] || fileInputDrop?.files?.[0];

            if (!selectedFile) {
                showError(window.SELECT_FILE_MESSAGE || 'Please select a file');
                return;
            }

            formData.append(fieldName, selectedFile);
        }

        // Hide previous results
        hideResult();
        hideDownload();

        // Show loading animation
        showLoading();

        // Disable form
        setFormDisabled(true);

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
            const response = await fetch(window.API_URL, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN
                },
                body: formData
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
            hideLoading();

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
                    <div class="w-full max-w-xs bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div class="bg-blue-600 h-2 rounded-full animate-progress" style="width: 0%"></div>
                    </div>
                </div>
            </div>
        `;
        container.classList.remove('hidden');

        // Simulate progress
        let progress = 0;
        const progressBar = container.querySelector('.animate-progress');
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 95) progress = 95;
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
        }, 200);

        // Store interval to clear later
        container.dataset.interval = interval;
    }

    function hideLoading() {
        const container = document.getElementById('loadingContainer');
        if (!container) return;

        const interval = container.dataset.interval;
        if (interval) {
            clearInterval(interval);
        }

        container.classList.add('hidden');
    }

    function showDownloadButton(originalFileName, blob) {
        const container = document.getElementById('downloadContainer');
        if (!container) return;

        // Generate output filename
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
                        <button id="downloadButton"
                                class="flex-1 inline-flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 active:scale-95">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                            </svg>
                            <span>${window.DOWNLOAD_BUTTON_TEXT || 'Download File'}</span>
                        </button>
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

        // Scroll to download button
        setTimeout(() => {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);

        // Download button handler with showSaveFilePicker
        const downloadBtn = document.getElementById('downloadButton');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', async () => {
                const originalExt = outputFileName.includes('.') ? outputFileName.slice(outputFileName.lastIndexOf('.')) : '.pdf';
                let finalName = outputFileName;

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
                        finalName = handle.name || outputFileName;
                        downloadBtn.classList.add('bg-green-700');
                        downloadBtn.innerHTML = '<span>✓ ' + (window.DOWNLOAD_BUTTON_TEXT || 'Download File') + '</span>';
                        setTimeout(() => {
                            downloadBtn.classList.remove('bg-green-700');
                            downloadBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg><span>' + (window.DOWNLOAD_BUTTON_TEXT || 'Download File') + '</span>';
                        }, 2000);
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

                // Fallback: prompt for filename, then trigger download (browser will ask location)
                const input = prompt(window.SAVE_AS_PROMPT || 'Save file as', outputFileName);
                if (input && input.trim()) {
                    finalName = input.trim();
                    const originalExt = outputFileName.includes('.') ? outputFileName.slice(outputFileName.lastIndexOf('.')) : '.pdf';
                    if (originalExt && !finalName.toLowerCase().endsWith(originalExt.toLowerCase())) {
                        finalName += originalExt;
                    }
                }

                const a = document.createElement('a');
                a.href = url;
                a.download = finalName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            });
        }
    }

    function hideDownload() {
        const container = document.getElementById('downloadContainer');
        if (container) {
            container.classList.add('hidden');
        }
    }

    function showError(message) {
        const container = document.getElementById('editorResult');
        if (!container) return;

        container.innerHTML = `
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
        container.classList.remove('hidden');
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

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    }

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
