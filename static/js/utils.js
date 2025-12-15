/**
 * Common Utilities for Convertica
 * Shared functions used across multiple components
 */

/**
 * Format file size in human-readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size (e.g., "1.5 MB")
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show error message in appropriate container
 * @param {string} message - Error message to display
 * @param {string} containerId - Optional container ID (defaults to finding first available)
 */
function showError(message, containerId = null) {
    // Find error container
    let container = null;

    if (containerId) {
        container = document.getElementById(containerId);
    } else {
        // Try common container IDs in order of preference
        const containerIds = ['converterResult', 'editorResult', 'errorMessage'];
        for (const id of containerIds) {
            container = document.getElementById(id);
            if (container) break;
        }
    }

    if (!container) {
        // Fallback: create error div dynamically
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-lg animate-fade-in mt-6';
        errorDiv.innerHTML = `
            <div class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div>
                    <h4 class="font-semibold text-red-800 mb-1">${window.ERROR_TITLE || 'Error'}</h4>
                    <p class="text-red-700 text-sm">${escapeHtml(message)}</p>
                </div>
            </div>
        `;

        // Insert after file input
        const fileInput = document.getElementById('fileInput') || document.getElementById('fileInputDrop');
        if (fileInput && fileInput.parentNode) {
            fileInput.parentNode.insertBefore(errorDiv, fileInput.nextSibling);
        }
        return;
    }

    // Use standardized error HTML
    const errorHtml = `
        <div class="bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-lg animate-fade-in">
            <div class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div>
                    <h4 class="font-semibold text-red-800 mb-1">${window.ERROR_TITLE || 'Error'}</h4>
                    <p class="text-red-700 text-sm">${escapeHtml(message)}</p>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = errorHtml;
    container.classList.remove('hidden');

    // Only scroll for converter pages, not for PDF editors
    if (container.id === 'converterResult') {
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

/**
 * Hide error message
 * @param {string} containerId - Optional container ID
 */
function hideError(containerId = null) {
    const containerIds = containerId
        ? [containerId]
        : ['converterResult', 'editorResult', 'errorMessage'];

    containerIds.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.classList.add('hidden');
            container.innerHTML = '';
        }
    });
}

/**
 * Show loading animation with progress bar
 * @param {string} containerId - Container ID (default: 'loadingContainer')
 * @param {Object} options - Options for customization
 */
function showLoading(containerId = 'loadingContainer', options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const title = options.title || window.LOADING_TITLE || 'Processing your file...';
    const message = options.message || window.LOADING_MESSAGE || 'Please wait, this may take a few moments';
    const showProgress = options.showProgress !== false; // Default to true

    // Translations for the patience message
    const patienceTitle = window.PATIENCE_TITLE || "Everything is going well!";
    const patienceMessage = window.PATIENCE_MESSAGE || "Large files take a bit longer. Please don't close this page — your file is being processed.";

    container.innerHTML = `
        <div class="bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-8 sm:p-12 shadow-lg border-2 border-blue-200">
            <div class="flex flex-col items-center justify-center space-y-6">
                <!-- Animated Spinner -->
                <div class="relative">
                    <div class="w-20 h-20 sm:w-24 sm:h-24 border-8 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                    <div class="absolute inset-0 flex items-center justify-center">
                        <svg class="w-10 h-10 sm:w-12 sm:h-12 text-blue-600 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
                        </svg>
                    </div>
                </div>

                <!-- Loading Text -->
                <div class="text-center">
                    <h3 class="text-xl sm:text-2xl font-bold text-gray-800 mb-2">${title}</h3>
                    <p class="text-gray-600 text-sm sm:text-base mb-4">${message}</p>
                </div>

                ${showProgress ? `
                <!-- Progress Bar with Percentage -->
                <div class="w-full max-w-md">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm font-semibold text-gray-700">Progress</span>
                        <span id="progressPercentage" class="text-sm font-bold text-blue-600">0%</span>
                    </div>
                    <div class="h-3 bg-blue-100 rounded-full overflow-hidden shadow-inner">
                        <div id="progressBar"
                             class="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 rounded-full transition-all duration-300 ease-out"
                             style="width: 0%">
                        </div>
                    </div>
                    <p id="progressStatusText" class="text-xs text-gray-500 mt-2 text-center">Processing your file...</p>
                </div>
                ` : ''}

                <!-- Patience Message (hidden initially, shown after 40 seconds) -->
                <div id="patienceMessage" class="hidden w-full max-w-md animate-fade-in">
                    <div class="bg-gradient-to-r from-emerald-100 to-teal-100 border-2 border-emerald-400 rounded-xl p-4 sm:p-5 shadow-md">
                        <div class="flex items-start space-x-3">
                            <div class="flex-shrink-0">
                                <div class="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center shadow-sm">
                                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                    </svg>
                                </div>
                            </div>
                            <div>
                                <h4 class="font-bold text-emerald-800 text-base mb-1">${patienceTitle}</h4>
                                <p class="text-emerald-700 text-sm">${patienceMessage}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <style>
            @keyframes fade-in {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .animate-fade-in {
                animation: fade-in 0.5s ease-out forwards;
            }
        </style>
    `;

    container.classList.remove('hidden');
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Show patience message after 40 seconds
    container._patienceTimeout = setTimeout(() => {
        const patienceMsg = document.getElementById('patienceMessage');
        if (patienceMsg) {
            patienceMsg.classList.remove('hidden');
            // Smooth scroll to show the message
            patienceMsg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }, 40000); // 40 seconds

    if (showProgress) {
        // Animate progress
        let progress = 0;
        const progressInterval = 200; // Update every 200ms
        const progressStep = 1.5; // Increase by 1.5% each time
        const maxProgress = 95; // Don't go to 100% until conversion is done

        const progressBar = document.getElementById('progressBar');
        const progressPercentage = document.getElementById('progressPercentage');

        const updateProgress = () => {
            if (progress < maxProgress) {
                progress += progressStep;
                // Slow down as we approach max (more realistic)
                if (progress > 70) {
                    progress += progressStep * 0.5;
                }
                if (progress > 85) {
                    progress += progressStep * 0.3;
                }

                if (progress > maxProgress) {
                    progress = maxProgress;
                }

                if (progressBar && progressPercentage) {
                    progressBar.style.width = `${progress}%`;
                    progressPercentage.textContent = `${Math.round(progress)}%`;
                }
            }
        };

        // Store interval ID so we can clear it later
        container._progressInterval = setInterval(updateProgress, progressInterval);
    }
}

/**
 * Hide loading animation
 * @param {string} containerId - Container ID (default: 'loadingContainer')
 * @param {boolean} showComplete - Whether to show 100% before hiding (default: false)
 */
function hideLoading(containerId = 'loadingContainer', showComplete = false) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Clear progress interval if it exists
    if (container._progressInterval) {
        clearInterval(container._progressInterval);
        container._progressInterval = null;
    }

    // Clear patience message timeout if it exists
    if (container._patienceTimeout) {
        clearTimeout(container._patienceTimeout);
        container._patienceTimeout = null;
    }

    // Only show 100% if explicitly requested (file is actually ready)
    if (showComplete) {
        const progressBar = document.getElementById('progressBar');
        const progressPercentage = document.getElementById('progressPercentage');

        if (progressBar && progressPercentage) {
            progressBar.style.width = '100%';
            progressPercentage.textContent = '100%';

            // Wait a moment to show 100%, then hide
            setTimeout(() => {
                container.classList.add('hidden');
            }, 500);
            return;
        }
    }

    // Just hide immediately without showing 100%
    container.classList.add('hidden');
}

/**
 * Show download button with modern file picker support
 * @param {Blob} blob - File blob to download
 * @param {string} originalFileName - Original file name
 * @param {string} containerId - Container ID (default: 'downloadContainer')
 * @param {Object} options - Options for customization
 */
async function showDownloadButton(blob, originalFileName, containerId = 'downloadContainer', options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Generate download filename
    let downloadName = originalFileName;
    if (window.REPLACE_REGEX && window.REPLACE_TO) {
        try {
            const regex = new RegExp(window.REPLACE_REGEX, 'i');
            downloadName = originalFileName.replace(regex, window.REPLACE_TO);
        } catch (e) {
            console.warn('Invalid regex pattern:', window.REPLACE_REGEX);
        }
    }

    // Create blob URL
    const blobUrl = URL.createObjectURL(blob);

    const successTitle = options.successTitle || window.SUCCESS_TITLE || 'Conversion Complete!';
    const successMessage = options.successMessage || window.SUCCESS_MESSAGE || 'Your file is ready to download';
    const downloadButtonText = options.downloadButtonText || window.DOWNLOAD_BUTTON_TEXT || 'Download File';
    const convertAnotherText = options.convertAnotherText || window.CONVERT_ANOTHER_TEXT || 'Convert another file';
    const showConvertAnother = options.showConvertAnother !== false; // Default to true

    container.innerHTML = `
        <div class="bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl p-6 sm:p-8 shadow-lg border-2 border-green-200 animate-fade-in">
            <div class="flex flex-col items-center justify-center space-y-4">
                <!-- Success Icon -->
                <div class="relative">
                    <div class="w-16 h-16 sm:w-20 sm:h-20 bg-green-500 rounded-full flex items-center justify-center shadow-lg animate-scale-in">
                        <svg class="w-10 h-10 sm:w-12 sm:h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <div class="absolute inset-0 bg-green-400 rounded-full animate-ping opacity-75"></div>
                </div>

                <!-- Success Message -->
                <div class="text-center">
                    <h3 class="text-xl sm:text-2xl font-bold text-gray-800 mb-2">${successTitle}</h3>
                    <p class="text-gray-600 text-sm sm:text-base mb-4">${successMessage}</p>
                    <p class="text-xs text-gray-500 font-mono">${escapeHtml(downloadName)}</p>
                </div>

                <!-- Download Button -->
                <button id="downloadButton"
                        class="group relative bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold py-4 px-8 sm:px-12 rounded-xl shadow-lg hover:shadow-2xl transform hover:scale-105 active:scale-95 transition-all duration-200 flex items-center space-x-3">
                    <svg class="w-6 h-6 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                    </svg>
                    <span>${downloadButtonText}</span>
                </button>

                ${showConvertAnother ? `
                <!-- Convert Another Button -->
                <button id="convertAnotherButton"
                        class="text-gray-600 hover:text-blue-600 font-medium text-sm sm:text-base transition-colors">
                    ${convertAnotherText}
                </button>
                ` : ''}
            </div>
        </div>
    `;

    container.classList.remove('hidden');
    // Scroll to download button with a slight delay to ensure DOM is updated
    setTimeout(() => {
        container.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);

    // Download button handler
    const downloadBtn = document.getElementById('downloadButton');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async () => {
            const originalExt = downloadName.includes('.') ? downloadName.slice(downloadName.lastIndexOf('.')) : '';
            let finalName = downloadName;

            // Try modern file picker to let user choose directory & filename
            if (window.showSaveFilePicker) {
                try {
                    const handle = await window.showSaveFilePicker({
                        suggestedName: downloadName,
                        types: originalExt
                            ? [{ description: 'File', accept: { '*/*': [originalExt] } }]
                            : undefined,
                    });
                    const writable = await handle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    finalName = handle.name || downloadName;
                    downloadBtn.classList.add('bg-green-600');
                    setTimeout(() => downloadBtn.classList.remove('bg-green-600'), 200);
                    return;
                } catch (err) {
                    // If user cancels, just exit silently; otherwise fall back
                    if (err && err.name === 'AbortError') {
                        return;
                    }
                    // Fallback to prompt flow below
                }
            }

            // Fallback: prompt for filename, then trigger download (browser will ask location)
            const input = prompt(window.SAVE_AS_PROMPT || 'Save file as', downloadName);
            if (input && input.trim()) {
                finalName = input.trim();
                if (originalExt && !finalName.toLowerCase().endsWith(originalExt.toLowerCase())) {
                    finalName += originalExt;
                }
            }

            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = finalName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            downloadBtn.classList.add('bg-green-600');
            setTimeout(() => downloadBtn.classList.remove('bg-green-600'), 200);
        });
    }

    // Convert another button handler (if exists)
    if (showConvertAnother) {
        const convertAnotherBtn = document.getElementById('convertAnotherButton');
        if (convertAnotherBtn && options.onConvertAnother) {
            convertAnotherBtn.addEventListener('click', options.onConvertAnother);
        }
    }

    // Cleanup blob URL after 10 minutes
    setTimeout(() => {
        URL.revokeObjectURL(blobUrl);
    }, 600000);
}

/**
 * Hide download container
 * @param {string} containerId - Container ID (default: 'downloadContainer')
 */
function hideDownload(containerId = 'downloadContainer') {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.add('hidden');
    }
}

/**
 * Update progress bar with real value from server
 * @param {number} progress - Progress percentage (0-100)
 * @param {string} message - Optional status message
 */
function updateProgress(progress, message = null) {
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    const progressMessage = document.querySelector('#loadingContainer .text-xs.text-gray-500');

    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
    if (progressPercentage) {
        progressPercentage.textContent = `${Math.round(progress)}%`;
    }
    if (progressMessage && message) {
        progressMessage.textContent = message;
    }
}

/**
 * Submit form as async task and poll for progress
 * This avoids Cloudflare timeout issues for long operations
 *
 * @param {Object} options - Configuration options
 * @param {string} options.apiUrl - API endpoint URL
 * @param {FormData} options.formData - Form data to submit
 * @param {string} options.csrfToken - CSRF token
 * @param {string} options.originalFileName - Original file name for download
 * @param {string} options.loadingContainerId - Loading container ID
 * @param {string} options.downloadContainerId - Download container ID
 * @param {string} options.errorContainerId - Error container ID
 * @param {Function} options.onSuccess - Callback on success (receives blob, filename)
 * @param {Function} options.onError - Callback on error
 * @param {Function} options.onProgress - Callback on progress update
 * @param {boolean} options.useAsync - Whether to use async mode (default: auto-detect based on file size)
 * @returns {Promise<void>}
 */
async function submitAsyncConversion(options) {
    const {
        apiUrl,
        formData,
        csrfToken,
        originalFileName,
        loadingContainerId = 'loadingContainer',
        downloadContainerId = 'downloadContainer',
        errorContainerId = 'converterResult',
        onSuccess,
        onError,
        onProgress,
        useAsync = null,
    } = options;

    // Determine if we should use async mode
    // Use async for files > 5MB or if explicitly requested
    let asyncMode = useAsync;
    if (asyncMode === null) {
        const file = formData.get('file') || formData.get('pdf_file') || formData.get('word_file');
        if (file && file.size) {
            asyncMode = file.size > 5 * 1024 * 1024; // 5MB threshold
        } else {
            asyncMode = false;
        }
    }

    // Show loading
    showLoading(loadingContainerId, { showProgress: true });

    // Stop fake progress animation - we'll use real progress
    const loadingContainer = document.getElementById(loadingContainerId);
    if (loadingContainer && loadingContainer._progressInterval) {
        clearInterval(loadingContainer._progressInterval);
        loadingContainer._progressInterval = null;
    }

    try {
        // Submit the conversion request
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            body: formData,
        });

        // Check if this is an async response (202 Accepted with task_id)
        if (response.status === 202) {
            const data = await response.json();
            const taskId = data.task_id;

            if (!taskId) {
                throw new Error('No task ID received');
            }

            // Poll for task status
            await pollTaskStatus(taskId, {
                onProgress: (progress, message) => {
                    updateProgress(progress, message);
                    if (onProgress) onProgress(progress, message);
                },
                onSuccess: async (result) => {
                    // Update progress to show downloading
                    updateProgress(95, 'Downloading result...');

                    // Download the result
                    const resultResponse = await fetch(`/api/tasks/${taskId}/result/`, {
                        method: 'GET',
                        headers: {
                            'X-CSRFToken': csrfToken,
                        },
                    });

                    if (!resultResponse.ok) {
                        throw new Error('Failed to download result');
                    }

                    const blob = await resultResponse.blob();
                    const filename = result.output_filename || originalFileName;

                    // Now file is truly ready - show 100%
                    updateProgress(100, 'Complete!');
                    hideLoading(loadingContainerId, true);

                    if (onSuccess) {
                        onSuccess(blob, filename);
                    } else {
                        await showDownloadButton(blob, filename, downloadContainerId);
                    }

                    // Cleanup task files after download
                    try {
                        await fetch(`/api/tasks/${taskId}/result/`, {
                            method: 'DELETE',
                            headers: { 'X-CSRFToken': csrfToken },
                        });
                    } catch (e) {
                        // Ignore cleanup errors
                    }
                },
                onError: (error) => {
                    hideLoading(loadingContainerId);
                    const errorMsg = error || 'Conversion failed';
                    showError(errorMsg, errorContainerId);
                    if (onError) onError(errorMsg);
                },
            });

        } else if (response.ok) {
            // Synchronous response - file is ready
            updateProgress(95, 'Downloading...');

            const blob = await response.blob();
            const contentDisposition = response.headers.get('content-disposition');
            let filename = originalFileName;

            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            // Now file is truly ready - show 100%
            updateProgress(100, 'Complete!');
            hideLoading(loadingContainerId, true);

            if (onSuccess) {
                onSuccess(blob, filename);
            } else {
                await showDownloadButton(blob, filename, downloadContainerId);
            }

        } else {
            // Error response
            let errorMsg = 'Conversion failed';
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorData.detail || errorMsg;
            } catch (e) {
                // Couldn't parse error JSON
            }

            hideLoading(loadingContainerId);
            showError(errorMsg, errorContainerId);
            if (onError) onError(errorMsg);
        }

    } catch (error) {
        hideLoading(loadingContainerId);
        const errorMsg = error.message || 'An error occurred';
        showError(errorMsg, errorContainerId);
        if (onError) onError(errorMsg);
    }
}

/**
 * Poll task status until complete or failed
 * @param {string} taskId - Task ID to poll
 * @param {Object} callbacks - Callback functions
 * @param {Function} callbacks.onProgress - Called with (progress, message)
 * @param {Function} callbacks.onSuccess - Called with result object
 * @param {Function} callbacks.onError - Called with error message
 * @param {number} pollInterval - Polling interval in ms (default: 1000)
 * @param {number} maxAttempts - Maximum poll attempts (default: 600 = 10 minutes)
 */
async function pollTaskStatus(taskId, callbacks, pollInterval = 2500, maxAttempts = 300) {
    const { onProgress, onSuccess, onError } = callbacks;
    let attempts = 0;

    const poll = async () => {
        attempts++;

        if (attempts > maxAttempts) {
            onError('Task timed out. Please try again with a smaller file.');
            return;
        }

        try {
            const response = await fetch(`/api/tasks/${taskId}/status/`);
            const data = await response.json();

            switch (data.status) {
                case 'SUCCESS':
                    // Don't show 100% yet - let onSuccess handle it after file is downloaded
                    onProgress(90, 'Preparing download...');
                    onSuccess(data);
                    break;

                case 'FAILURE':
                    onError(data.error || 'Conversion failed');
                    break;

                case 'PROGRESS':
                    onProgress(data.progress || 0, data.current_step || 'Processing...');
                    setTimeout(poll, pollInterval);
                    break;

                case 'PENDING':
                    onProgress(0, data.message || 'Waiting in queue...');
                    setTimeout(poll, pollInterval);
                    break;

                case 'STARTED':
                    onProgress(5, data.message || 'Processing started...');
                    setTimeout(poll, pollInterval);
                    break;

                default:
                    // Unknown status - keep polling
                    setTimeout(poll, pollInterval);
            }

        } catch (error) {
            // Network error - retry
            if (attempts < maxAttempts) {
                setTimeout(poll, pollInterval * 2); // Back off on errors
            } else {
                onError('Lost connection to server');
            }
        }
    };

    // Start polling
    poll();
}

// Export functions to global scope
if (typeof window !== 'undefined') {
    window.formatFileSize = formatFileSize;
    window.escapeHtml = escapeHtml;
    window.showError = showError;
    window.hideError = hideError;
    window.showLoading = showLoading;
    window.hideLoading = hideLoading;
    window.showDownloadButton = showDownloadButton;
    window.hideDownload = hideDownload;
    window.updateProgress = updateProgress;
    window.submitAsyncConversion = submitAsyncConversion;
    window.pollTaskStatus = pollTaskStatus;
}
