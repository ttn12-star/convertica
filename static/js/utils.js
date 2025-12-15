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
                    <p class="text-xs text-gray-500 mt-2 text-center">Processing your file...</p>
                </div>
                ` : ''}
            </div>
        </div>
    `;

    container.classList.remove('hidden');
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

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
 */
function hideLoading(containerId = 'loadingContainer') {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Clear progress interval if it exists
    if (container._progressInterval) {
        clearInterval(container._progressInterval);
        container._progressInterval = null;
    }

    // Animate to 100% before hiding
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');

    if (progressBar && progressPercentage) {
        progressBar.style.width = '100%';
        progressPercentage.textContent = '100%';

        // Wait a moment to show 100%, then hide
        setTimeout(() => {
            container.classList.add('hidden');
        }, 300);
    } else {
        container.classList.add('hidden');
    }
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
}
