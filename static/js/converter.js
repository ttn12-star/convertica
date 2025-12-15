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

    const fileInput = document.getElementById('fileInput');
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
        const selectedFile = fileInput?.files?.[0] || fileInputDrop?.files?.[0];

        if (!selectedFile) {
            window.showError(window.SELECT_FILE_MESSAGE || 'Please select a file', 'converterResult');
            return;
        }

        // Validate PDF page count using universal function
        if (selectedFile.type === 'application/pdf') {
            try {
                const isValid = await window.validatePdfPageLimit(selectedFile);
                if (!isValid) {
                    hideLoading();
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

        // Ensure loading container exists
        if (!loadingContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(loadingContainer, form.nextSibling);
        }

        // Show loading animation
        window.showLoading('loadingContainer');

        // Disable form
        setFormDisabled(true);

        const formData = new FormData();
        const fieldName = window.FILE_INPUT_NAME || 'file';
        formData.append(fieldName, selectedFile);

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

        // Add Turnstile token if available
        const turnstileResponse = document.querySelector('[name="cf-turnstile-response"]');
        if (turnstileResponse && turnstileResponse.value) {
            formData.append('turnstile_token', turnstileResponse.value);
        }

        // Ensure containers exist
        if (!loadingContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(loadingContainer, form.nextSibling);
        }
        if (!downloadContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(downloadContainer, loadingContainer.nextSibling || form.nextSibling);
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
        }

        // Determine if this is a heavy operation that should use async mode
        // PDF to Word, Word to PDF, PDF to Excel are heavy operations
        const heavyOperations = ['pdf_to_word', 'word_to_pdf', 'pdf_to_excel'];
        const isHeavyOperation = heavyOperations.includes(conversionType);
        const isLargeFile = selectedFile.size > 3 * 1024 * 1024; // 3MB

        // Use async mode for heavy operations or large files
        const useAsync = isHeavyOperation || isLargeFile;

        // Use async API endpoint for heavy operations
        let apiUrl = window.API_URL;
        if (useAsync && isHeavyOperation && !apiUrl.endsWith('/async/')) {
            // Append /async/ to the URL for async processing
            apiUrl = apiUrl.replace(/\/$/, '') + '/async/';
        }

        try {
            await window.submitAsyncConversion({
                apiUrl: apiUrl,
                formData: formData,
                csrfToken: window.CSRF_TOKEN || '',
                originalFileName: selectedFile.name,
                loadingContainerId: 'loadingContainer',
                downloadContainerId: 'downloadContainer',
                errorContainerId: 'converterResult',
                useAsync: useAsync,
                onSuccess: (blob, filename) => {
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
                                    selectFileButton.focus();
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
