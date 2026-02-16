/**
 * File Converter Component
 * Handles file conversion with loading animation and download button
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('converterForm');
    if (!form) return;

    // Turnstile callback to ensure token is present on submit
    window.onTurnstileSuccess = function(token) {
        let tokenInput = form.querySelector('[name="turnstile_token"]');
        if (!tokenInput) {
            tokenInput = document.createElement('input');
            tokenInput.type = 'hidden';
            tokenInput.name = 'turnstile_token';
            form.appendChild(tokenInput);
        }
        tokenInput.value = token;
    };

    const submitButton = form.querySelector('button[type="submit"]');
    const resultContainer = document.getElementById('converterResult');

    // Create loading animation container
    const loadingContainer = document.createElement('div');
    loadingContainer.id = 'loadingContainer';
    loadingContainer.className = 'hidden mt-6';

    // Create download button container
    const downloadContainer = document.createElement('div');
    downloadContainer.id = 'downloadContainer';
    downloadContainer.className = 'hidden mt-6';

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get file from either input
        const fileInput = document.getElementById('fileInput');
        const fileInputDrop = document.getElementById('fileInputDrop');
        const selectedFiles = (fileInput?.files && fileInput.files.length > 0)
            ? fileInput.files
            : (fileInputDrop?.files && fileInputDrop.files.length > 0)
                ? fileInputDrop.files
                : null;
        const selectedFile = selectedFiles?.[0];

        const isBatchMode = Boolean(
            window.BATCH_ENABLED &&
            window.IS_PREMIUM &&
            selectedFiles &&
            selectedFiles.length > 1 &&
            window.BATCH_API_URL &&
            window.BATCH_FIELD_NAME
        );

        if (!selectedFile) {
            window.showError(window.SELECT_FILE_MESSAGE || 'Please select a file', 'converterResult');
            return;
        }

        // Validate PDF page count using universal function (single file only)
        if (!isBatchMode && selectedFile.type === 'application/pdf') {
            try {
                const isValid = await window.validatePdfPageLimit(selectedFile);
                if (!isValid) {
                    // Note: loading not shown yet at this point, but call for safety
                    window.hideLoading('loadingContainer');
                    setFormDisabled(false);
                    return;
                }
            } catch (error) {
                console.error('PDF validation error:', error);
                // Continue with conversion if validation fails
            }
        }

        // Hide previous results
        hideResult();
        hideDownload();

        // Ensure containers exist (do this once before showing loading)
        if (!loadingContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(loadingContainer, form.nextSibling);
        }
        if (!downloadContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(downloadContainer, loadingContainer.nextSibling || form.nextSibling);
        }

        // Show loading animation (disable progress bar for batch mode)
        window.showLoading('loadingContainer', { showProgress: !isBatchMode });

        // Disable form
        setFormDisabled(true);

        const formData = new FormData();
        const singleFieldName = window.FILE_INPUT_NAME || 'file';
        if (isBatchMode) {
            const batchFieldName = window.BATCH_FIELD_NAME;
            Array.from(selectedFiles).forEach((f) => {
                formData.append(batchFieldName, f);
            });
        } else {
            formData.append(singleFieldName, selectedFile);
        }

        // Add pages parameter if available (for PDF to JPG)
        const pagesInput = form.querySelector('input[name="pages"]');
        if (pagesInput && pagesInput.value) {
            formData.append('pages', pagesInput.value);
        }

        // Add DPI parameter if available (for PDF to JPG)
        const dpiSelect = form.querySelector('select[name="dpi"]');
        if (dpiSelect && dpiSelect.value) {
            formData.append('dpi', dpiSelect.value);
        }

        // Add OCR parameter if available (only for PDF to Word)
        const ocrCheckbox = form.querySelector('input[name="ocr_enabled"]');
        if (ocrCheckbox) {
            formData.append('ocr_enabled', ocrCheckbox.checked ? 'true' : 'false');
        }

        // Add OCR language if available (only for PDF to Word)
        const ocrLanguageSelect = form.querySelector('select[name="ocr_language"]');
        if (ocrLanguageSelect) {
            formData.append('ocr_language', ocrLanguageSelect.value);
            console.log('OCR Debug: Sending language:', ocrLanguageSelect.value);
        } else {
            console.log('OCR Debug: ocr_language select not found');
        }

        // Add Turnstile token if available
        const turnstileResponse = document.querySelector('[name="cf-turnstile-response"]');
        if (turnstileResponse && turnstileResponse.value) {
            formData.append('turnstile_token', turnstileResponse.value);
        }


        // Determine conversion type from API URL or page path
        let conversionType = window.CONVERSION_TYPE || '';
        if (!conversionType) {
            // Try to determine from API URL
            const apiUrl = window.API_URL || '';
            if (apiUrl.includes('pdf-to-word')) conversionType = 'pdf_to_word';
            else if (apiUrl.includes('word-to-pdf')) conversionType = 'word_to_pdf';
            else if (apiUrl.includes('pdf-to-excel')) conversionType = 'pdf_to_excel';
            else if (apiUrl.includes('pdf-to-jpg')) conversionType = 'pdf_to_jpg';
            else if (apiUrl.includes('jpg-to-pdf')) conversionType = 'jpg_to_pdf';
            else if (apiUrl.includes('epub-to-pdf')) conversionType = 'epub_to_pdf';
            else if (apiUrl.includes('pdf-to-epub')) conversionType = 'pdf_to_epub';
            else if (apiUrl.includes('compress')) conversionType = 'compress_pdf';
        }

        // Heavy operations that always use async mode
        const heavyOperations = [
            'pdf_to_word',
            'word_to_pdf',
            'pdf_to_excel',
            'epub_to_pdf',
            'pdf_to_epub'
        ];
        // Operations that use async for large files (> 5MB)
        const mediumOperations = ['pdf_to_jpg', 'compress_pdf'];

        const isHeavyOperation = heavyOperations.includes(conversionType);
        const isMediumOperation = mediumOperations.includes(conversionType);
        const isLargeFile = selectedFile.size > 5 * 1024 * 1024; // 5MB

        // Use async mode for:
        // - Heavy operations (PDF to Word, Word to PDF, PDF to Excel) - always
        // - Medium operations (PDF to JPG, Compress) - for large files
        // - Any other operation - for very large files (> 10MB)
        const useAsync = (!isBatchMode) && (
                        isHeavyOperation ||
                        (isMediumOperation && isLargeFile) ||
                        (selectedFile.size > 10 * 1024 * 1024)
                    );

        // Use async API endpoint for operations that need it
        let apiUrl = isBatchMode ? window.BATCH_API_URL : window.API_URL;
        const needsAsyncEndpoint = (isHeavyOperation || isMediumOperation) && useAsync;
        if (needsAsyncEndpoint && !apiUrl.endsWith('/async/')) {
            // Append /async/ to the URL for async processing
            apiUrl = apiUrl.replace(/\/$/, '') + '/async/';
        }

        // Set cancel callback so the cancel button can restore the form
        window._onCancelCallback = () => {
            window.hideLoading('loadingContainer');
            setFormDisabled(false);
        };

        try {
            await window.submitAsyncConversion({
                apiUrl: apiUrl,
                formData: formData,
                csrfToken: window.CSRF_TOKEN || '',
                originalFileName: isBatchMode ? 'convertica.zip' : selectedFile.name,
                loadingContainerId: 'loadingContainer',
                downloadContainerId: 'downloadContainer',
                errorContainerId: 'converterResult',
                useAsync: useAsync,
                onBackground: () => {
                    // User sent task to background — restore form
                    setFormDisabled(false);
                },
                onSuccess: (blob, filename, response) => {
                    // Check for batch failures
                    if (isBatchMode && response && response.headers) {
                        const failedCount = parseInt(response.headers.get('X-Convertica-Batch-Failed-Count') || '0');
                        const successCount = parseInt(response.headers.get('X-Convertica-Batch-Count') || '0');

                        if (failedCount > 0) {
                            const totalCount = successCount + failedCount;
                            const warningMsg = failedCount === 1
                                ? `Warning: 1 file out of ${totalCount} failed to convert and was excluded from the archive. Check the file for corruption or try re-saving it.`
                                : `Warning: ${failedCount} files out of ${totalCount} failed to convert and were excluded from the archive. Check these files for corruption or try re-saving them.`;

                            window.showError(warningMsg, 'converterResult');
                        }
                    }

                    window.showDownloadButton(blob, filename, 'downloadContainer', {
                        onConvertAnother: () => {
                            resetSelectedFileUI();
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
                },
                onError: (errorMsg) => {
                    setFormDisabled(false);
                },
                onProgress: (progress, message) => {
                    // Progress is updated automatically by submitAsyncConversion
                    // This callback can be used for additional UI updates if needed
                }
            });

        } catch (err) {
            if (typeof console !== 'undefined' && console.error) {
                console.error('Conversion error:', err);
            }
            window.hideLoading('loadingContainer');
            window.showError(err.message || window.ERROR_MESSAGE, 'converterResult');
        } finally {
            setFormDisabled(false);
        }
    });

    function hideDownload() {
        window.hideDownload('downloadContainer');
    }

    function resetSelectedFileUI() {
        const fileInput = document.getElementById('fileInput');
        const fileInputDrop = document.getElementById('fileInputDrop');
        const selectedFileDiv = document.getElementById('selectedFile');
        const fileInfo = document.getElementById('fileInfo');

        if (fileInput) fileInput.value = '';
        if (fileInputDrop) fileInputDrop.value = '';
        if (selectedFileDiv) selectedFileDiv.classList.add('hidden');
        if (fileInfo) fileInfo.classList.remove('hidden');

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }


    function hideResult() {
        if (resultContainer) {
            resultContainer.classList.add('hidden');
        }
    }

    function clearError() {
        if (resultContainer) {
            resultContainer.classList.add('hidden');
            resultContainer.innerHTML = '';
        }
    }

    function setFormDisabled(disabled) {
        if (submitButton) {
            submitButton.disabled = disabled;
            if (disabled) {
                submitButton.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
        const fileInput = document.getElementById('fileInput');
        const fileInputDrop = document.getElementById('fileInputDrop');
        if (fileInput) {
            fileInput.disabled = disabled;
        }
        if (fileInputDrop) {
            fileInputDrop.disabled = disabled;
        }
    }
});
