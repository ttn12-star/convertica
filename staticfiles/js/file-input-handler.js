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
    // Try to find either convertButton (for converter pages) or editButton (for editor pages)
    const convertButton = document.getElementById('convertButton') || document.getElementById('editButton');

    // Only proceed if we have the essential elements
    if (!fileInput) return;
    // dropZone is optional (not all pages have it)

    // Use formatFileSize from utils.js if available, otherwise define locally
    const formatFileSize = window.formatFileSize || function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    // Show selected file and enable convert button
    // Universal PDF page count validator - used across all pages
    window.validatePdfPageLimit = async function(file) {
        try {
            if (file.type !== 'application/pdf') {
                return true; // Not a PDF file, no validation needed
            }

            if (typeof pdfjsLib === 'undefined') {
                console.warn('PDF.js not loaded, skipping page validation');
                return true; // PDF.js not available, allow file
            }

            if (typeof window.PAGE_LIMIT_ERROR === 'undefined') {
                console.warn('PAGE_LIMIT_ERROR not defined, skipping page validation');
                return true; // Translation not available, allow file
            }

            const arrayBuffer = await file.arrayBuffer();
            const pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            const pageCount = pdfDoc.numPages;
            const maxPages = 50; // Same as backend

            if (pageCount > maxPages) {
                // Show error using universal function with translation fallback
                const errorMessage = getPageLimitError(pageCount, maxPages);
                showUniversalError(errorMessage);

                return false;
            }

            // Clear any previous errors
            clearAllErrors();
            return true;

        } catch (error) {
            console.error('Error validating PDF pages:', error);
            return true; // Allow file if validation fails
        }
    };

    // Clear errors from all possible containers
    function clearAllErrors() {
        // Clear converterResult
        const converterResult = document.getElementById('converterResult');
        if (converterResult) {
            converterResult.classList.add('hidden');
            converterResult.innerHTML = '';
        }

        // Clear editorResult
        const editorResult = document.getElementById('editorResult');
        if (editorResult) {
            editorResult.classList.add('hidden');
            editorResult.innerHTML = '';
        }

        // Clear errorMessage
        const errorMessageDiv = document.getElementById('errorMessage');
        if (errorMessageDiv) {
            errorMessageDiv.classList.add('hidden');
            errorMessageDiv.textContent = '';
        }

        // Clear inline error
        clearInlineError();
    }

    // Universal error display function - works for all containers
    function showUniversalError(message) {
        // Find the first available error container
        const containers = [
            document.getElementById('converterResult'),
            document.getElementById('editorResult'),
            document.getElementById('errorMessage')
        ];

        const container = containers.find(c => c !== null);

        if (container) {
            // Use the same error HTML for all containers
            const errorHtml = `
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

            container.innerHTML = errorHtml;
            container.classList.remove('hidden');
            // Only scroll for converter pages, not for PDF editors
            if (container.id === 'converterResult') {
                container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        } else {
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
                        <p class="text-red-700 text-sm">${message}</p>
                    </div>
                </div>
            `;

            // Insert after file input
            const fileInput = document.getElementById('fileInput') || document.getElementById('fileInputDrop');
            if (fileInput && fileInput.parentNode) {
                fileInput.parentNode.insertBefore(errorDiv, fileInput.nextSibling);
            }
        }
    }

    // Get translated page limit error with fallback
    function getPageLimitError(pageCount, maxPages) {
        if (typeof window.PAGE_LIMIT_ERROR !== 'undefined') {
            return window.PAGE_LIMIT_ERROR.replace('%(page_count)d', pageCount).replace('%(max_pages)d', maxPages);
        } else {
            // Fallback to English if translation not available
            return `PDF has ${pageCount} pages, maximum allowed is ${maxPages}. Please split your PDF into smaller parts.`;
        }
    }

    // Clear inline error
    function clearInlineError() {
        // Clear all possible error containers
        const containers = [
            document.getElementById('converterResult'),
            document.getElementById('editorResult'),
            document.getElementById('errorMessage')
        ];

        containers.forEach(container => {
            if (container) {
                container.classList.add('hidden');
                container.innerHTML = '';
            }
        });

        // Clear any dynamically created error divs
        const dynamicErrors = document.querySelectorAll('.bg-red-50.border-red-200');
        dynamicErrors.forEach(error => error.remove());
    }


    function showSelectedFile(file) {
        if (!selectedFileDiv || !fileName || !fileSize) return;

        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        selectedFileDiv.classList.remove('hidden');
        if (fileInfo) {
            fileInfo.classList.add('hidden');
        }

        // Validate PDF page count using universal function
        if (file.type === 'application/pdf') {
            window.validatePdfPageLimit(file).then(isValid => {
                if (!isValid) {
                    // Disable convert button if validation fails
                    if (convertButton) {
                        convertButton.disabled = true;
                        convertButton.classList.add('opacity-50', 'cursor-not-allowed');
                    }
                } else {
                    // Enable convert button if validation passes
                    if (convertButton) {
                        convertButton.disabled = false;
                        convertButton.classList.remove('opacity-50', 'cursor-not-allowed');
                    }
                }
            }).catch(error => {
                console.error('PDF validation error:', error);
                // Enable button by default if validation fails
                if (convertButton) {
                    convertButton.disabled = false;
                    convertButton.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            });
        } else {
            // Enable convert button for non-PDF files
            if (convertButton) {
                convertButton.disabled = false;
                convertButton.classList.remove('opacity-50', 'cursor-not-allowed');
            }
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

        // Disable convert/edit button
        if (convertButton) {
            convertButton.disabled = true;
            convertButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    const DROP_HIT_MARGIN_PX = 240; // Allow generous near-miss drops within this margin

    // Create a clone of a FileList that can be assigned to inputs (cross-browser)
    function cloneFileList(files, allowMultiple = true) {
        if (!files || files.length === 0) return null;
        // DataTransfer constructor is not available in some browsers (e.g., older Firefox/Safari)
        if (typeof DataTransfer !== 'undefined') {
            const dt = new DataTransfer();
            const source = allowMultiple ? Array.from(files) : [files[0]];
            source.forEach((file) => dt.items.add(file));
            return dt.files;
        }
        // Fallback: return original FileList (assignment works in modern browsers)
        return allowMultiple ? files : files;
    }

    // Sync files between two inputs
    function syncFileInputs(sourceInput, targetInput) {
        if (sourceInput.files && sourceInput.files.length > 0) {
            const cloned = cloneFileList(sourceInput.files);
            if (cloned) {
                targetInput.files = cloned;
            }
        }
    }

    // Check if pointer is within drop zone or within a margin
    function isNearDropZone(e, zone, marginPx = DROP_HIT_MARGIN_PX) {
        if (!zone || !e) return false;
        const rect = zone.getBoundingClientRect();
        const x = e.clientX;
        const y = e.clientY;
        return (
            x >= rect.left - marginPx &&
            x <= rect.right + marginPx &&
            y >= rect.top - marginPx &&
            y <= rect.bottom + marginPx
        );
    }

    // Button click handler
    // Note: Don't preventDefault to allow other handlers to work
    if (selectFileButton && fileInput) {
        selectFileButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Small delay to ensure input is ready (fixes double-click issue)
            setTimeout(() => {
                fileInput.click();
            }, 0);
        });
    }

    // File input change (from button)
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                // Sync to fileInputDrop
                if (fileInputDrop) {
                    syncFileInputs(fileInput, fileInputDrop);
                }
                showSelectedFile(file);

                // Dispatch custom event for other scripts (like organize-pdf.js)
                const customEvent = new CustomEvent('fileSelected', {
                    detail: { file: file },
                    bubbles: true
                });
                document.dispatchEvent(customEvent);
            }
        });
    }

    // File input change (from drop zone)
    if (fileInputDrop) {
        fileInputDrop.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const file = e.target.files[0];
                // Sync to fileInput so pdf-crop-editor.js can pick it up
                if (fileInput) {
                    syncFileInputs(fileInputDrop, fileInput);
                    // Trigger change event on fileInput to ensure pdf-crop-editor.js handles it
                    // Use setTimeout to ensure sync happens first
                    setTimeout(() => {
                        if (fileInput.files && fileInput.files.length > 0) {
                            const changeEvent = new Event('change', { bubbles: true });
                            fileInput.dispatchEvent(changeEvent);
                        }
                    }, 0);
                }
                showSelectedFile(file);

                // Dispatch custom event for other scripts (like organize-pdf.js)
                const customEvent = new CustomEvent('fileSelected', {
                    detail: { file: file },
                    bubbles: true
                });
                document.dispatchEvent(customEvent);
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

    // Drag and drop handlers (only if dropZone exists)
    if (dropZone) {
        let dragCounter = 0; // Track nested drag events
        let isHoveringDropZone = false;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        dropZone.addEventListener('dragenter', (e) => {
            dragCounter++;
            isHoveringDropZone = true;
            dropZone.classList.add('border-blue-500', 'bg-blue-100', 'border-4');
            dropZone.classList.remove('border-2', 'border-gray-300', 'bg-gray-50');
        }, false);

        dropZone.addEventListener('dragover', (e) => {
            // Keep highlighting during drag over
            isHoveringDropZone = true;
            dropZone.classList.add('border-blue-500', 'bg-blue-100', 'border-4');
            dropZone.classList.remove('border-2', 'border-gray-300', 'bg-gray-50');
        }, false);

        dropZone.addEventListener('dragleave', (e) => {
            dragCounter--;
            if (dragCounter === 0) {
                isHoveringDropZone = false;
                dropZone.classList.remove('border-blue-500', 'bg-blue-100', 'border-4');
                dropZone.classList.add('border-2', 'border-gray-300', 'bg-gray-50');
            }
        }, false);

        function handleDrop(e) {
            dragCounter = 0;
            isHoveringDropZone = false;
            dropZone.classList.remove('border-blue-500', 'bg-blue-100', 'border-4');
            dropZone.classList.add('border-2', 'border-gray-300', 'bg-gray-50');

            const dt = e.dataTransfer;
            const files = dt ? dt.files : null;

            if (files && files.length > 0) {
                const allowMultiple = fileInputDrop && fileInputDrop.hasAttribute('multiple');
                const cloned = cloneFileList(files, allowMultiple);

                // Set files to both inputs
                if (fileInput && cloned) {
                    fileInput.files = cloned;
                }
                if (fileInputDrop && cloned) {
                    fileInputDrop.files = cloned;
                }

                showSelectedFile(files[0]);

                // Trigger change event on both inputs to ensure all handlers pick it up
                if (fileInput) {
                    const event = new Event('change', { bubbles: true });
                    fileInput.dispatchEvent(event);
                }
                if (fileInputDrop) {
                    const event = new Event('change', { bubbles: true });
                    fileInputDrop.dispatchEvent(event);
                }

                // Dispatch custom event for other scripts (like organize-pdf.js)
                const customEvent = new CustomEvent('fileSelected', {
                    detail: { file: files[0] },
                    bubbles: true
                });
                document.dispatchEvent(customEvent);
            }
        }

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            handleDrop(e);
        }, false);

        // Accept drops that are close to the zone (near-miss)
        ['dragover', 'drop'].forEach((eventName) => {
            document.addEventListener(eventName, (e) => {
                const near = isNearDropZone(e, dropZone, DROP_HIT_MARGIN_PX);
                if (!near && eventName === 'dragover') {
                    // Remove highlight if we drifted away
                    isHoveringDropZone = false;
                    dropZone.classList.remove('border-blue-500', 'bg-blue-100', 'border-4');
                    dropZone.classList.add('border-2', 'border-gray-300', 'bg-gray-50');
                    return;
                }
                if (!near) return;
                e.preventDefault();
                e.stopPropagation();
                if (eventName === 'dragover') {
                    isHoveringDropZone = true;
                    dropZone.classList.add('border-blue-500', 'bg-blue-100', 'border-4');
                    dropZone.classList.remove('border-2', 'border-gray-300', 'bg-gray-50');
                } else if (eventName === 'drop') {
                    handleDrop(e);
                }
            }, true);
        });

        // Fallback: if drop happens while zone is highlighted (hover state), accept it
        document.addEventListener('drop', (e) => {
            const near = isNearDropZone(e, dropZone, DROP_HIT_MARGIN_PX);
            if (!isHoveringDropZone && !near) return;
            e.preventDefault();
            e.stopPropagation();
            handleDrop(e);
        }, true);

        // Remove click handler - drop zone is for drag & drop only
        // Users should use the "Select file" button to browse files
    }
});
