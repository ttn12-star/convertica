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

    // Remove file from list
    function removeFile(index) {
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

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

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
        showLoading();
        
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
            hideLoading();
            showDownloadButton(blob, generateDownloadName());

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

    function showLoading() {
        if (!loadingContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(loadingContainer, form.nextSibling);
        }
        
        let progress = 0;
        const progressInterval = 200;
        const progressStep = 1.5;
        const maxProgress = 95;
        
        loadingContainer.innerHTML = `
            <div class="bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-8 sm:p-12 shadow-lg border-2 border-blue-200">
                <div class="flex flex-col items-center justify-center space-y-6">
                    <div class="relative">
                        <div class="w-20 h-20 sm:w-24 sm:h-24 border-8 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                        <div class="absolute inset-0 flex items-center justify-center">
                            <svg class="w-10 h-10 sm:w-12 sm:h-12 text-blue-600 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
                            </svg>
                        </div>
                    </div>
                    
                    <div class="text-center">
                        <h3 class="text-xl sm:text-2xl font-bold text-gray-800 mb-2">${window.LOADING_TITLE || 'Converting your images...'}</h3>
                        <p class="text-gray-600 text-sm sm:text-base mb-4">${window.LOADING_MESSAGE || 'Please wait, this may take a few moments'}</p>
                    </div>
                    
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
                        <p class="text-xs text-gray-500 mt-2 text-center">Processing ${selectedFiles.length} image(s)...</p>
                    </div>
                </div>
            </div>
        `;
        
        loadingContainer.classList.remove('hidden');
        loadingContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        const progressBar = document.getElementById('progressBar');
        const progressPercentage = document.getElementById('progressPercentage');
        
        const updateProgress = () => {
            if (progress < maxProgress) {
                progress += progressStep;
                if (progress > 70) progress += progressStep * 0.5;
                if (progress > 85) progress += progressStep * 0.3;
                if (progress > maxProgress) progress = maxProgress;
                
                if (progressBar && progressPercentage) {
                    progressBar.style.width = `${progress}%`;
                    progressPercentage.textContent = `${Math.round(progress)}%`;
                }
            }
        };
        
        loadingContainer._progressInterval = setInterval(updateProgress, progressInterval);
    }

    function hideLoading() {
        if (loadingContainer._progressInterval) {
            clearInterval(loadingContainer._progressInterval);
            loadingContainer._progressInterval = null;
        }
        
        const progressBar = document.getElementById('progressBar');
        const progressPercentage = document.getElementById('progressPercentage');
        
        if (progressBar && progressPercentage) {
            progressBar.style.width = '100%';
            progressPercentage.textContent = '100%';
            
            setTimeout(() => {
                loadingContainer.classList.add('hidden');
            }, 300);
        } else {
            loadingContainer.classList.add('hidden');
        }
    }

    function showDownloadButton(blob, downloadName) {
        if (!downloadContainer.parentNode && form.parentNode) {
            form.parentNode.insertBefore(downloadContainer, form.nextSibling);
        }
        
        const blobUrl = URL.createObjectURL(blob);
        
        downloadContainer.innerHTML = `
            <div class="bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl p-6 sm:p-8 shadow-lg border-2 border-green-200 animate-fade-in">
                <div class="flex flex-col items-center justify-center space-y-4">
                    <div class="relative">
                        <div class="w-16 h-16 sm:w-20 sm:h-20 bg-green-500 rounded-full flex items-center justify-center shadow-lg animate-scale-in">
                            <svg class="w-10 h-10 sm:w-12 sm:h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <div class="absolute inset-0 bg-green-400 rounded-full animate-ping opacity-75"></div>
                    </div>
                    
                    <div class="text-center">
                        <h3 class="text-xl sm:text-2xl font-bold text-gray-800 mb-2">${window.SUCCESS_TITLE || 'Conversion Complete!'}</h3>
                        <p class="text-gray-600 text-sm sm:text-base mb-4">${window.SUCCESS_MESSAGE || 'Your PDF is ready to download'}</p>
                        <p class="text-xs text-gray-500 font-mono">${escapeHtml(downloadName)}</p>
                    </div>
                    
                    <button id="downloadButton" 
                            class="group relative bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold py-4 px-8 sm:px-12 rounded-xl shadow-lg hover:shadow-2xl transform hover:scale-105 active:scale-95 transition-all duration-200 flex items-center space-x-3">
                        <svg class="w-6 h-6 group-hover:animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        <span>${window.DOWNLOAD_BUTTON_TEXT || 'Download PDF'}</span>
                    </button>
                    
                    <button id="convertAnotherButton" 
                            class="text-gray-600 hover:text-blue-600 font-medium text-sm sm:text-base transition-colors">
                        ${window.CONVERT_ANOTHER_TEXT || 'Convert another file'}
                    </button>
                </div>
            </div>
        `;
        
        downloadContainer.classList.remove('hidden');
        downloadContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        const downloadBtn = document.getElementById('downloadButton');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                const a = document.createElement('a');
                a.href = blobUrl;
                a.download = downloadName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                downloadBtn.classList.add('bg-green-600');
                setTimeout(() => {
                    downloadBtn.classList.remove('bg-green-600');
                }, 200);
            });
        }
        
        const convertAnotherBtn = document.getElementById('convertAnotherButton');
        if (convertAnotherBtn) {
            convertAnotherBtn.addEventListener('click', () => {
                selectedFiles = [];
                updateFileList();
                updateConvertButton();
                
                if (fileInput) fileInput.value = '';
                if (fileInputDrop) fileInputDrop.value = '';
                
                hideDownload();
                hideResult();
                setFormDisabled(false);
                
                if (selectFileButton) {
                    selectFileButton.focus();
                }
            });
        }
        
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
                        <p class="text-red-700 text-sm">${escapeHtml(message)}</p>
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

