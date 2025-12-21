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
    const convertButton = document.getElementById('convertButton') || document.getElementById('editButton');

    if (!fileInput) return;

    const formatFileSize = window.formatFileSize || function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    // === PDF page limit validation ===
    window.validatePdfPageLimit = async function(file) {
        try {
            if (file.type !== 'application/pdf') return true;

            // Ждем пока PDF.js будет загружен
            if (typeof pdfjsLib === 'undefined') {
                console.info('PDF.js not loaded yet, skipping PDF page validation');
                return true;
            }

            if (typeof window.PAGE_LIMIT_ERROR === 'undefined') {
                console.info('PAGE_LIMIT_ERROR not defined, skipping PDF page validation');
                return true;
            }

            const arrayBuffer = await file.arrayBuffer();
            const pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            const pageCount = pdfDoc.numPages;
            const maxPages = 50;

            if (pageCount > maxPages) {
                const errorMessage = getPageLimitError(pageCount, maxPages);
                if (errorMessage) {
                    showUniversalError(errorMessage);
                    return false;
                }
                // Premium users - no error shown, continue processing
            }

            clearInlineError();
            return true;
        } catch (error) {
            console.error('Error validating PDF pages:', error);
            return true;
        }
    };

    function clearAllErrors() {
        ['converterResult', 'editorResult', 'errorMessage'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.classList.add('hidden');
                el.innerHTML = '';
            }
        });
        clearInlineError();
    }

    function showUniversalError(message) {
        const containers = ['converterResult', 'editorResult', 'errorMessage']
            .map(id => document.getElementById(id))
            .filter(Boolean);
        const container = containers[0];

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

        if (container) {
            container.innerHTML = errorHtml;
            container.classList.remove('hidden');
            if (container.id === 'converterResult') {
                container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        } else {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-lg animate-fade-in mt-6';
            errorDiv.innerHTML = errorHtml;
            const fileEl = fileInput || fileInputDrop;
            if (fileEl && fileEl.parentNode) {
                fileEl.parentNode.insertBefore(errorDiv, fileEl.nextSibling);
            }
        }
    }

    function getPageLimitError(pageCount, maxPages) {
        // Don't show error for premium users
        if (window.IS_PREMIUM) {
            return null;
        }

        if (window.PAGE_LIMIT_ERROR) {
            const message = window.PAGE_LIMIT_ERROR.replace('%(page_count)d', pageCount).replace('%(max_pages)d', maxPages);
            const linkText = "get a 1-day Premium subscription for just $1";

            if (window.PREMIUM_LINK && message.includes(linkText)) {
                const link = `<a href="${window.PREMIUM_LINK}" class="text-amber-600 hover:text-amber-700 font-medium underline">${linkText}</a>`;
                return message.replace(linkText, link);
            }
            return message;
        } else {
            return `PDF has ${pageCount} pages (limit: 50). You can split your file into smaller parts or <a href="/users/premium/" class="text-amber-600 hover:text-amber-700 font-medium underline">get a 1-day Premium subscription for just $1</a> to process files without limits!`;
        }
    }

    function clearInlineError() {
        ['converterResult', 'editorResult', 'errorMessage'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.classList.add('hidden');
                el.innerHTML = '';
            }
        });
        document.querySelectorAll('.bg-red-50.border-red-200').forEach(el => el.remove());
    }

    function showSelectedFile(file) {
        if (!selectedFileDiv || !fileName || !fileSize) return;

        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        selectedFileDiv.classList.remove('hidden');
        if (fileInfo) fileInfo.classList.add('hidden');

        if (file.type === 'application/pdf') {
            window.validatePdfPageLimit(file).then(isValid => {
                if (convertButton) {
                    convertButton.disabled = !isValid;
                    convertButton.classList.toggle('opacity-50', !isValid);
                    convertButton.classList.toggle('cursor-not-allowed', !isValid);
                }
            }).catch(() => {
                if (convertButton) {
                    convertButton.disabled = false;
                    convertButton.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            });
        } else {
            if (convertButton) {
                convertButton.disabled = false;
                convertButton.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
    }

    function hideSelectedFile() {
        if (selectedFileDiv) selectedFileDiv.classList.add('hidden');
        if (fileInfo) fileInfo.classList.remove('hidden');
        if (fileInput) fileInput.value = '';
        if (fileInputDrop) fileInputDrop.value = '';
        if (convertButton) {
            convertButton.disabled = true;
            convertButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    const DROP_HIT_MARGIN_PX = 240;

    function cloneFileList(files, allowMultiple = true) {
        if (!files || files.length === 0) return null;
        if (typeof DataTransfer !== 'undefined') {
            const dt = new DataTransfer();
            const source = allowMultiple ? Array.from(files) : [files[0]];
            source.forEach(f => dt.items.add(f));
            return dt.files;
        }
        return allowMultiple ? files : files;
    }

    function syncFileInputs(sourceInput, targetInput) {
        if (sourceInput.files && sourceInput.files.length > 0) {
            const cloned = cloneFileList(sourceInput.files);
            if (cloned) targetInput.files = cloned;
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
