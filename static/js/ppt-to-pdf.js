/**
 * PowerPoint to PDF converter JavaScript functionality.
 * Handles file upload, conversion, and progress tracking.
 */

class PowerPointToPDFConverter {
    constructor() {
        this.form = document.getElementById('pptToPdfForm');
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('pptFile');
        this.browseBtn = document.getElementById('browseBtn');
        this.fileInfo = document.getElementById('fileInfo');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        this.removeFileBtn = document.getElementById('removeFile');
        this.batchSection = document.getElementById('batchSection');
        this.enableBatchBtn = document.getElementById('enableBatch');
        this.convertBtn = document.getElementById('convertBtn');
        this.progressSection = document.getElementById('progressSection');
        this.progressBar = document.getElementById('progressBar');
        this.progressPercent = document.getElementById('progressPercent');
        this.progressMessage = document.getElementById('progressMessage');
        this.resultSection = document.getElementById('resultSection');
        this.downloadLink = document.getElementById('downloadLink');
        this.convertAnotherBtn = document.getElementById('convertAnother');

        this.currentFile = null;
        this.isBatchMode = false;
        this.isPremium = false;

        this.init();
    }

    init() {
        // Check if user is premium
        this.checkPremiumStatus();

        // File input handlers
        this.browseBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));

        // Drag and drop handlers
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('border-orange-500', 'bg-orange-50');
        });

        this.dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('border-orange-500', 'bg-orange-50');
        });

        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('border-orange-500', 'bg-orange-50');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });

        // Remove file handler
        this.removeFileBtn.addEventListener('click', () => this.removeFile());

        // Batch processing handler
        this.enableBatchBtn.addEventListener('click', () => this.enableBatchMode());

        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Convert another file
        this.convertAnotherBtn.addEventListener('click', () => this.resetForm());
    }

    checkPremiumStatus() {
        // Check if user is premium (this would typically come from backend)
        fetch('/api/user-info/')
            .then(response => response.json())
            .then(data => {
                this.isPremium = data.is_premium || false;
                if (this.isPremium) {
                    this.batchSection.classList.remove('hidden');
                }
            })
            .catch(error => {
                console.log('Could not check premium status:', error);
            });
    }

    handleFileSelect(file) {
        if (!file) return;

        // Validate file type
        const validTypes = [
            'application/vnd.ms-powerpoint', // .ppt
            'application/vnd.openxmlformats-officedocument.presentationml.presentation', // .pptx
            'application/octet-stream'
        ];

        const validExtensions = ['.ppt', '.pptx'];
        const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));

        if (!validTypes.includes(file.type) && !validExtensions.includes(fileExtension)) {
            this.showError('Please select a valid PowerPoint file (.ppt or .pptx)');
            return;
        }

        // Validate file size (50MB for free users, 200MB for premium)
        const maxSize = this.isPremium ? 200 * 1024 * 1024 : 50 * 1024 * 1024;
        if (file.size > maxSize) {
            const maxSizeMB = maxSize / (1024 * 1024);
            this.showError(`File size exceeds ${maxSizeMB}MB limit`);
            return;
        }

        this.currentFile = file;
        this.displayFileInfo();
        this.convertBtn.disabled = false;
        this.dropZone.classList.add('hidden');
        this.fileInfo.classList.remove('hidden');
    }

    displayFileInfo() {
        this.fileName.textContent = this.currentFile.name;
        this.fileSize.textContent = window.formatFileSize ?
            window.formatFileSize(this.currentFile.size) :
            `${(this.currentFile.size / 1024 / 1024).toFixed(2)} MB`;
    }

    removeFile() {
        this.currentFile = null;
        this.fileInput.value = '';
        this.convertBtn.disabled = true;
        this.dropZone.classList.remove('hidden');
        this.fileInfo.classList.add('hidden');
        this.resetProgress();
    }

    enableBatchMode() {
        this.isBatchMode = true;
        this.enableBatchBtn.textContent = 'Batch Mode Enabled';
        this.enableBatchBtn.disabled = true;
        this.enableBatchBtn.classList.add('bg-purple-700');

        // Update form to accept multiple files
        this.fileInput.multiple = true;
        this.fileInput.accept = '.ppt,.pptx,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation';

        // Update UI text
        const dropZoneText = this.dropZone.querySelector('p.text-lg');
        dropZoneText.textContent = 'Drop your PowerPoint files here or click to browse (up to 20 files)';

        const dropZoneSubtext = this.dropZone.querySelector('p.text-sm');
        dropZoneSubtext.textContent = 'Support for .ppt and .pptx files up to 200MB each (Premium)';
    }

    async handleSubmit(e) {
        e.preventDefault();

        if (!this.currentFile) {
            this.showError('Please select a file to convert');
            return;
        }

        this.showProgress();

        const formData = new FormData();

        if (this.isBatchMode) {
            // Handle batch conversion
            const files = Array.from(this.fileInput.files);

            if (files.length > 20) {
                this.showError('Maximum 20 files allowed for batch processing');
                return;
            }

            files.forEach((file, index) => {
                formData.append(`ppt_files[${index}]`, file);
            });

            this.updateProgress(10, 'Preparing batch conversion...');

            try {
                const response = await fetch('/api/ppt-to-pdf/batch/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': this.form.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });

                const result = await response.json();

                if (response.ok) {
                    this.updateProgress(100, 'Batch conversion completed!');
                    this.showBatchResult(result);
                } else {
                    throw new Error(result.error || 'Batch conversion failed');
                }
            } catch (error) {
                this.showError(error.message);
                this.hideProgress();
            }
        } else {
            // Handle single file conversion
            formData.append('ppt_file', this.currentFile);

            this.updateProgress(10, 'Converting PowerPoint to PDF...');

            try {
                const response = await fetch('/api/ppt-to-pdf/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': this.form.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });

                const result = await response.json();

                if (response.ok) {
                    this.updateProgress(100, 'Conversion completed!');
                    this.showResult(result);
                } else {
                    throw new Error(result.error || 'Conversion failed');
                }
            } catch (error) {
                this.showError(error.message);
                this.hideProgress();
            }
        }
    }

    showProgress() {
        this.progressSection.classList.remove('hidden');
        this.resultSection.classList.add('hidden');
        this.convertBtn.disabled = true;
        this.updateProgress(0, 'Starting conversion...');
    }

    updateProgress(percent, message) {
        this.progressBar.style.width = `${percent}%`;
        this.progressPercent.textContent = `${percent}%`;
        this.progressMessage.textContent = message;
    }

    hideProgress() {
        this.progressSection.classList.add('hidden');
        this.convertBtn.disabled = false;
    }

    showResult(result) {
        this.hideProgress();
        this.resultSection.classList.remove('hidden');

        if (result.download_url) {
            this.downloadLink.href = result.download_url;
            this.downloadLink.download = this.currentFile.name.replace(/\.(ppt|pptx)$/i, '.pdf');
        }
    }

    showBatchResult(result) {
        this.hideProgress();
        this.resultSection.classList.remove('hidden');

        // For batch results, create a download button for each file
        const downloadContainer = this.resultSection.querySelector('.mt-4');
        downloadContainer.innerHTML = '';

        if (result.results && Array.isArray(result.results)) {
            result.results.forEach((fileResult, index) => {
                const downloadBtn = document.createElement('a');
                downloadBtn.href = fileResult.download_url;
                downloadBtn.className = 'block w-full px-4 py-2 bg-green-600 text-white text-center rounded-lg hover:bg-green-700 transition-colors mb-2';
                downloadBtn.download = fileResult.filename || `converted_${index + 1}.pdf`;
                downloadBtn.textContent = `Download ${fileResult.filename || `File ${index + 1}`}`;
                downloadContainer.appendChild(downloadBtn);
            });
        }

        // Add "Convert Another" button
        const convertAnotherBtn = document.createElement('button');
        convertAnotherBtn.type = 'button';
        convertAnotherBtn.className = 'w-full px-4 py-2 border border-green-600 text-green-600 rounded-lg hover:bg-green-50 transition-colors';
        convertAnotherBtn.textContent = 'Convert More Files';
        convertAnotherBtn.addEventListener('click', () => this.resetForm());
        downloadContainer.appendChild(convertAnotherBtn);
    }

    showError(message) {
        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed top-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg z-50';
        errorDiv.innerHTML = `
            <div class="flex items-center space-x-3">
                <svg class="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                    <h3 class="text-sm font-medium text-red-900">Error</h3>
                    <p class="text-sm text-red-700">${message}</p>
                </div>
                <button type="button" class="text-red-500 hover:text-red-700" onclick="this.parentElement.parentElement.remove()">
                    <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(errorDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }

    resetProgress() {
        this.progressBar.style.width = '0%';
        this.progressPercent.textContent = '0%';
        this.progressMessage.textContent = 'Please wait while we convert your PowerPoint file to PDF...';
    }

    resetForm() {
        this.removeFile();
        this.hideProgress();
        this.resultSection.classList.add('hidden');
        this.resetProgress();

        // Reset batch mode
        if (this.isBatchMode) {
            this.isBatchMode = false;
            this.fileInput.multiple = false;
            this.enableBatchBtn.textContent = 'Enable Batch Processing';
            this.enableBatchBtn.disabled = false;
            this.enableBatchBtn.classList.remove('bg-purple-700');

            // Reset UI text
            const dropZoneText = this.dropZone.querySelector('p.text-lg');
            dropZoneText.textContent = 'Drop your PowerPoint file here or click to browse';

            const dropZoneSubtext = this.dropZone.querySelector('p.text-sm');
            dropZoneSubtext.textContent = 'Support for .ppt and .pptx files up to 50MB';
        }
    }
}

// Initialize converter when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PowerPointToPDFConverter();
});
