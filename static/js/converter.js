/**
 * File Converter Component
 * Handles file conversion with loading animation and download button
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('converterForm');
    if (!form) return;

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
            showError(window.SELECT_FILE_MESSAGE || 'Please select a file');
            return;
        }

        // Hide previous results
        hideResult();
        hideDownload();

        // Show loading animation
        showLoading();

        // Disable form
        setFormDisabled(true);

        const formData = new FormData();
        const fieldName = window.FILE_INPUT_NAME || 'file';
        formData.append(fieldName, selectedFile);

        // Add hCaptcha token if available
        const hcaptchaResponse = document.querySelector('[name="h-captcha-response"]');
        if (hcaptchaResponse && hcaptchaResponse.value) {
            formData.append('hcaptcha_token', hcaptchaResponse.value);
        }

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
            hideLoading();
            showDownloadButton(blob, fileInput.files[0].name);

        } catch (err) {
            if (typeof console !== 'undefined' && console.error) {
                console.error('Conversion error:', err);
            }
            hideLoading();
            showError(err.message);
        } finally {
            setFormDisabled(false);
        }
    });

    function showLoading() {
        if (!loadingContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(loadingContainer, form.nextSibling);
        }

        // Initialize progress
        let progress = 0;
        const progressInterval = 200; // Update every 200ms
        const progressStep = 1.5; // Increase by 1.5% each time
        const maxProgress = 95; // Don't go to 100% until conversion is done

        loadingContainer.innerHTML = `
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
                        <h3 class="text-xl sm:text-2xl font-bold text-gray-800 mb-2">${window.LOADING_TITLE || 'Converting your file...'}</h3>
                        <p class="text-gray-600 text-sm sm:text-base mb-4">${window.LOADING_MESSAGE || 'Please wait, this may take a few moments'}</p>
                    </div>

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
                </div>
            </div>
        `;

        loadingContainer.classList.remove('hidden');
        loadingContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Animate progress
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
        loadingContainer._progressInterval = setInterval(updateProgress, progressInterval);
    }

    function hideLoading() {
        // Clear progress interval if it exists
        if (loadingContainer._progressInterval) {
            clearInterval(loadingContainer._progressInterval);
            loadingContainer._progressInterval = null;
        }

        // Animate to 100% before hiding
        const progressBar = document.getElementById('progressBar');
        const progressPercentage = document.getElementById('progressPercentage');

        if (progressBar && progressPercentage) {
            progressBar.style.width = '100%';
            progressPercentage.textContent = '100%';

            // Wait a moment to show 100%, then hide
            setTimeout(() => {
                loadingContainer.classList.add('hidden');
            }, 300);
        } else {
            loadingContainer.classList.add('hidden');
        }
    }

    function showDownloadButton(blob, originalFileName) {
        if (!downloadContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(downloadContainer, form.nextSibling);
        }

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

        downloadContainer.innerHTML = `
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
                        <h3 class="text-xl sm:text-2xl font-bold text-gray-800 mb-2">${window.SUCCESS_TITLE || 'Conversion Complete!'}</h3>
                        <p class="text-gray-600 text-sm sm:text-base mb-4">${window.SUCCESS_MESSAGE || 'Your file is ready to download'}</p>
                        <p class="text-xs text-gray-500 font-mono">${downloadName}</p>
                    </div>

                    <!-- Download Button -->
                    <button id="downloadButton"
                            class="group relative bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold py-4 px-8 sm:px-12 rounded-xl shadow-lg hover:shadow-2xl transform hover:scale-105 active:scale-95 transition-all duration-200 flex items-center space-x-3">
                        <svg class="w-6 h-6 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        <span>${window.DOWNLOAD_BUTTON_TEXT || 'Download File'}</span>
                    </button>

                    <!-- Convert Another Button -->
                    <button id="convertAnotherButton"
                            class="text-gray-600 hover:text-blue-600 font-medium text-sm sm:text-base transition-colors">
                        ${window.CONVERT_ANOTHER_TEXT || 'Convert another file'}
                    </button>
                </div>
            </div>
        `;

        downloadContainer.classList.remove('hidden');
        downloadContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Download button handler
        const downloadBtn = document.getElementById('downloadButton');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                const a = document.createElement('a');
                a.href = blobUrl;
                a.download = downloadName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);

                // Add visual feedback
                downloadBtn.classList.add('bg-green-600');
                setTimeout(() => {
                    downloadBtn.classList.remove('bg-green-600');
                }, 200);
            });
        }

        // Convert another button handler
        const convertAnotherBtn = document.getElementById('convertAnotherButton');
        if (convertAnotherBtn) {
            convertAnotherBtn.addEventListener('click', () => {
                const fileInput = document.getElementById('fileInput');
                const fileInputDrop = document.getElementById('fileInputDrop');
                const selectedFileDiv = document.getElementById('selectedFile');
                const fileInfo = document.getElementById('fileInfo');
                const convertButton = document.getElementById('convertButton');

                if (fileInput) fileInput.value = '';
                if (fileInputDrop) fileInputDrop.value = '';

                // Hide selected file display
                if (selectedFileDiv) {
                    selectedFileDiv.classList.add('hidden');
                }
                if (fileInfo) {
                    fileInfo.classList.remove('hidden');
                }

                // Disable convert button
                if (convertButton) {
                    convertButton.disabled = true;
                }

                hideDownload();
                hideResult();
                setFormDisabled(false);

                // Focus on select button
                const selectFileButton = document.getElementById('selectFileButton');
                if (selectFileButton) {
                    selectFileButton.focus();
                }
            });
        }

        // Cleanup blob URL after 10 minutes
        setTimeout(() => {
            URL.revokeObjectURL(blobUrl);
        }, 600000);
    }

    function hideDownload() {
        downloadContainer.classList.add('hidden');
    }

    function showError(message) {
        if (!resultContainer) return;

        resultContainer.innerHTML = `
            <div class="bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-lg animate-fade-in">
                <div class="flex items-start space-x-3">
                    <svg class="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <div>
                        <h4 class="font-semibold text-red-800 mb-1">${window.ERROR_TITLE || 'Error'}</h4>
                        <p class="text-red-700 text-sm">${message}</p>
                    </div>
                </div>
            </div>
        `;

        resultContainer.classList.remove('hidden');
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function hideResult() {
        if (resultContainer) {
            resultContainer.classList.add('hidden');
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
