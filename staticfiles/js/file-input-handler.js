/**
 * File Input Handler
 * Handles drag & drop, file selection display, and file removal
 */
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const fileInputDrop = document.getElementById('fileInputDrop');
    const selectFileButton = document.getElementById('selectFileButton');
    const addMoreFilesButton = document.getElementById('addMoreFilesButton');
    const dropZone = document.getElementById('dropZone');
    const selectedFileDiv = document.getElementById('selectedFile');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileInfo = document.getElementById('fileInfo');
    const removeFileBtn = document.getElementById('removeFile');
    const convertButton = document.getElementById('convertButton') || document.getElementById('editButton');

    if (!fileInput) return;

    let currentFiles = null;

    const PDFJS_VERSION = '3.11.174';

    function loadExternalScript(src) {
        return new Promise((resolve, reject) => {
            const existing = Array.from(document.scripts).find((s) => s.src === src);
            if (existing) {
                if (typeof window.pdfjsLib !== 'undefined') return resolve();
                existing.addEventListener('load', () => resolve(), { once: true });
                existing.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
                return;
            }

            const script = document.createElement('script');
            script.src = src;
            script.async = true;
            script.crossOrigin = 'anonymous';
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`Failed to load ${src}`));
            document.head.appendChild(script);
        });
    }

    async function ensurePdfJsLoaded() {
        if (typeof window.pdfjsLib !== 'undefined') return true;

        const candidates = [
            `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}/pdf.min.js`,
            `https://unpkg.com/pdfjs-dist@${PDFJS_VERSION}/build/pdf.min.js`,
        ];

        for (const src of candidates) {
            try {
                await loadExternalScript(src);
                if (typeof window.pdfjsLib !== 'undefined') break;
            } catch (e) {
                // try next
            }
        }

        if (typeof window.pdfjsLib === 'undefined') return false;

        try {
            if (!window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}/pdf.worker.min.js`;
            }
        } catch (e) {
            // ignore
        }

        return true;
    }

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

            // Premium users skip validation entirely
            if (window.IS_PREMIUM) {
                return true;
            }

            const pdfReady = await ensurePdfJsLoaded();
            if (!pdfReady) {
                return true;
            }

            if (typeof window.PAGE_LIMIT_ERROR === 'undefined') {
                console.info('PAGE_LIMIT_ERROR not defined, skipping PDF page validation');
                return true;
            }

            const arrayBuffer = await file.arrayBuffer();
            const pdfDoc = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            const pageCount = pdfDoc.numPages;
            const maxPages = Number(window.MAX_FREE_PDF_PAGES) || 30;

            if (pageCount > maxPages) {
                const errorMessage = getPageLimitError(pageCount, maxPages);
                if (errorMessage) {
                    showUniversalError(errorMessage);
                    return false;
                }
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

        // Escape HTML helper
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        if (window.PAGE_LIMIT_ERROR) {
            const message = window.PAGE_LIMIT_ERROR.replace('%(page_count)d', pageCount).replace('%(max_pages)d', maxPages);
            const linkText = "upgrade to Premium";

            if (window.PREMIUM_LINK && message.includes(linkText)) {
                const safeUrl = escapeHtml(window.PREMIUM_LINK);
                const safeLinkText = escapeHtml(linkText);
                const link = `<a href="${safeUrl}" class="text-amber-600 hover:text-amber-700 font-medium underline">${safeLinkText}</a>`;
                return escapeHtml(message).replace(escapeHtml(linkText), link);
            }
            return escapeHtml(message);
        } else {
            return `PDF has ${escapeHtml(String(pageCount))} pages (limit: ${escapeHtml(String(maxPages))}). You can split your file into smaller parts or <a href="/pricing/" class="text-amber-600 hover:text-amber-700 font-medium underline">upgrade to Premium</a> to process larger files with much higher limits!`;
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

    function showSelectedFile(files) {
        if (!selectedFileDiv || !fileName || !fileSize) return;

        const fileList = Array.from(files || []);
        const firstFile = fileList[0];
        if (!firstFile) return;

        const isBatchUi = Boolean(window.BATCH_ENABLED && window.IS_PREMIUM);
        if (isBatchUi && fileList.length > 1) {
            const totalSize = fileList.reduce((sum, f) => sum + (f.size || 0), 0);
            fileName.textContent = `${fileList.length} files selected`;
            fileSize.textContent = `Total: ${formatFileSize(totalSize)}`;
        } else {
            fileName.textContent = firstFile.name;
            fileSize.textContent = formatFileSize(firstFile.size);
        }

        selectedFileDiv.classList.remove('hidden');
        if (fileInfo) fileInfo.classList.add('hidden');

        if (addMoreFilesButton) {
            if (isBatchUi && fileList.length > 0 && fileList.length < 10) {
                addMoreFilesButton.classList.remove('hidden');
            } else {
                addMoreFilesButton.classList.add('hidden');
            }
        }

        // Only validate PDF page count for single-file PDF uploads
        // Skip validation entirely for batch mode (multiple files)
        if (fileList.length === 1 && firstFile.type === 'application/pdf') {
            window.validatePdfPageLimit(firstFile).then(isValid => {
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
            // Multiple files or non-PDF: always enable button
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
        if (addMoreFilesButton) addMoreFilesButton.classList.add('hidden');
        currentFiles = null;
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

    function mergeFileLists(existingFiles, newFiles, allowMultiple = true) {
        if (!newFiles || newFiles.length === 0) return existingFiles;
        if (!allowMultiple) return cloneFileList(newFiles, false);

        const existing = Array.from(existingFiles || []);
        const incoming = Array.from(newFiles || []);
        const merged = [];
        const seen = new Set();

        [...existing, ...incoming].forEach((f) => {
            if (!f) return;
            const key = `${f.name}::${f.size}::${f.lastModified}`;
            if (seen.has(key)) return;
            seen.add(key);
            merged.push(f);
        });

        // Hard limit to 10 in UI to match batch backend expectations
        const limited = merged.slice(0, 10);
        return cloneFileList(limited, true) || limited;
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

    if (addMoreFilesButton && fileInput) {
        addMoreFilesButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            setTimeout(() => {
                fileInput.click();
            }, 0);
        });
    }

    // File input change (from button)
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const allowMultiple = fileInput.hasAttribute('multiple');
                const merged = mergeFileLists(currentFiles, e.target.files, allowMultiple);
                if (merged) {
                    fileInput.files = merged;
                    currentFiles = merged;
                }

                // Sync to fileInputDrop
                if (fileInputDrop) {
                    syncFileInputs(fileInput, fileInputDrop);
                }

                showSelectedFile(fileInput.files);

                // Dispatch custom event for other scripts (keep backward compatibility)
                const firstFile = fileInput.files[0];
                const customEvent = new CustomEvent('fileSelected', {
                    detail: { file: firstFile, files: fileInput.files },
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
                const merged = mergeFileLists(currentFiles, files, allowMultiple);
                const cloned = cloneFileList(merged || files, allowMultiple);

                // Set files to both inputs
                if (fileInput && cloned) {
                    fileInput.files = cloned;
                }
                if (fileInputDrop && cloned) {
                    fileInputDrop.files = cloned;
                }

                if (cloned) {
                    currentFiles = cloned;
                }

                showSelectedFile(cloned || merged || files);

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
                const firstFile = (fileInput && fileInput.files && fileInput.files.length > 0)
                    ? fileInput.files[0]
                    : files[0];
                const customEvent = new CustomEvent('fileSelected', {
                    detail: {
                        file: firstFile,
                        files: (fileInput && fileInput.files && fileInput.files.length > 0) ? fileInput.files : files,
                    },
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
