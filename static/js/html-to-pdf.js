/**
 * HTML to PDF converter JavaScript functionality.
 * Handles HTML content and URL conversion with progress tracking.
 */

class HTMLToPDFConverter {
    constructor() {
        this.htmlContentForm = document.getElementById('htmlContentForm');
        this.urlForm = document.getElementById('urlForm');
        this.htmlContentTab = document.getElementById('htmlContentTab');
        this.urlTab = document.getElementById('urlTab');
        this.progressSection = document.getElementById('progressSection');
        this.progressBar = document.getElementById('progressBar');
        this.progressPercent = document.getElementById('progressPercent');
        this.progressMessage = document.getElementById('progressMessage');
        this.resultSection = document.getElementById('resultSection');
        this.downloadLink = document.getElementById('downloadLink');
        this.convertAnotherBtn = document.getElementById('convertAnother');

        this.currentMode = 'html'; // 'html' or 'url'
        this.isPremium = false;

        this.init();
    }

    init() {
        // Check if user is premium
        this.checkPremiumStatus();

        // Tab switching
        this.htmlContentTab.addEventListener('click', () => this.switchToHTMLMode());
        this.urlTab.addEventListener('click', () => this.switchToURLMode());

        // Form submissions
        this.htmlContentForm.addEventListener('submit', (e) => this.handleHTMLSubmit(e));
        this.urlForm.addEventListener('submit', (e) => this.handleURLSubmit(e));

        // Convert another
        this.convertAnotherBtn.addEventListener('click', () => this.resetForm());

        // Character counter for HTML content
        const htmlContent = document.getElementById('htmlContent');
        htmlContent.addEventListener('input', () => this.updateCharCounter());
    }

    checkPremiumStatus() {
        // Check if user is premium (this would typically come from backend)
        fetch('/api/user-info/')
            .then(response => response.json())
            .then(data => {
                this.isPremium = data.is_premium || false;
            })
            .catch(error => {
                console.log('Could not check premium status:', error);
            });
    }

    switchToHTMLMode() {
        this.currentMode = 'html';
        this.htmlContentForm.classList.remove('hidden');
        this.urlForm.classList.add('hidden');

        this.htmlContentTab.classList.add('bg-white', 'text-gray-900', 'shadow-sm');
        this.htmlContentTab.classList.remove('text-gray-500');

        this.urlTab.classList.remove('bg-white', 'text-gray-900', 'shadow-sm');
        this.urlTab.classList.add('text-gray-500');
    }

    switchToURLMode() {
        this.currentMode = 'url';
        this.htmlContentForm.classList.add('hidden');
        this.urlForm.classList.remove('hidden');

        this.urlTab.classList.add('bg-white', 'text-gray-900', 'shadow-sm');
        this.urlTab.classList.remove('text-gray-500');

        this.htmlContentTab.classList.remove('bg-white', 'text-gray-900', 'shadow-sm');
        this.htmlContentTab.classList.add('text-gray-500');
    }

    updateCharCounter() {
        const htmlContent = document.getElementById('htmlContent');
        const charCount = htmlContent.value.length;

        // Add character counter if it doesn't exist
        let counter = htmlContent.parentNode.querySelector('.char-counter');
        if (!counter) {
            counter = document.createElement('div');
            counter.className = 'text-sm text-gray-500 mt-1 char-counter';
            htmlContent.parentNode.appendChild(counter);
        }

        const maxChars = this.isPremium ? 100000 : 10000; // Premium gets higher limit
        counter.textContent = `${charCount.toLocaleString()} / ${maxChars.toLocaleString()} characters`;

        if (charCount > maxChars) {
            counter.classList.add('text-red-500');
            counter.classList.remove('text-gray-500');
        } else {
            counter.classList.remove('text-red-500');
            counter.classList.add('text-gray-500');
        }
    }

    async handleHTMLSubmit(e) {
        e.preventDefault();

        const htmlContent = document.getElementById('htmlContent').value.trim();
        if (!htmlContent) {
            this.showError('Please enter HTML content to convert');
            return;
        }

        // Check character limit
        const maxChars = this.isPremium ? 100000 : 10000;
        if (htmlContent.length > maxChars) {
            this.showError(`HTML content exceeds ${maxChars.toLocaleString()} character limit`);
            return;
        }

        // Validate HTML for security
        if (!this.validateHTMLContent(htmlContent)) {
            return;
        }

        this.showProgress();

        const formData = new FormData(this.htmlContentForm);

        this.updateProgress(10, 'Converting HTML to PDF...');

        try {
            const response = await fetch('/api/html-to-pdf/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.htmlContentForm.querySelector('[name=csrfmiddlewaretoken]').value
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

    async handleURLSubmit(e) {
        e.preventDefault();

        const url = document.getElementById('url').value.trim();
        if (!url) {
            this.showError('Please enter a URL to convert');
            return;
        }

        // Validate URL format
        try {
            new URL(url);
        } catch {
            this.showError('Please enter a valid URL');
            return;
        }

        this.showProgress();

        const formData = new FormData(this.urlForm);

        this.updateProgress(10, 'Fetching web page...');

        try {
            const response = await fetch('/api/url-to-pdf/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.urlForm.querySelector('[name=csrfmiddlewaretoken]').value
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

    validateHTMLContent(htmlContent) {
        // Basic security validation
        const dangerousPatterns = [
            /<script[^>]*>/i,
            /javascript:/i,
            /data:/i,
            /vbscript:/i,
            /<iframe[^>]*>/i,
            /<object[^>]*>/i,
            /<embed[^>]*>/i
        ];

        for (const pattern of dangerousPatterns) {
            if (pattern.test(htmlContent)) {
                this.showError('HTML contains potentially dangerous content that cannot be processed for security reasons');
                return false;
            }
        }

        return true;
    }

    showProgress() {
        this.progressSection.classList.remove('hidden');
        this.resultSection.classList.add('hidden');
        this.updateProgress(0, 'Starting conversion...');

        // Disable form buttons
        this.htmlContentForm.querySelector('button[type="submit"]').disabled = true;
        this.urlForm.querySelector('button[type="submit"]').disabled = true;
    }

    updateProgress(percent, message) {
        this.progressBar.style.width = `${percent}%`;
        this.progressPercent.textContent = `${percent}%`;
        this.progressMessage.textContent = message;
    }

    hideProgress() {
        this.progressSection.classList.add('hidden');

        // Re-enable form buttons
        this.htmlContentForm.querySelector('button[type="submit"]').disabled = false;
        this.urlForm.querySelector('button[type="submit"]').disabled = false;
    }

    showResult(result) {
        this.hideProgress();
        this.resultSection.classList.remove('hidden');

        if (result.download_url) {
            this.downloadLink.href = result.download_url;

            // Generate filename based on mode
            let filename = 'converted.pdf';
            if (this.currentMode === 'html') {
                const filenameInput = document.getElementById('filename').value;
                filename = filenameInput.endsWith('.pdf') ? filenameInput : `${filenameInput}.pdf`;
            } else {
                const filenameInput = document.getElementById('urlFilename').value;
                filename = filenameInput.endsWith('.pdf') ? filenameInput : `${filenameInput}.pdf`;
            }

            this.downloadLink.download = filename;
        }
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

    resetForm() {
        // Hide result and progress
        this.hideProgress();
        this.resultSection.classList.add('hidden');

        // Reset forms
        this.htmlContentForm.reset();
        this.urlForm.reset();

        // Reset progress bar
        this.progressBar.style.width = '0%';
        this.progressPercent.textContent = '0%';
        this.progressMessage.textContent = 'Please wait while we convert your content to PDF...';

        // Remove character counter
        const counter = document.querySelector('.char-counter');
        if (counter) {
            counter.remove();
        }
    }
}

// Initialize converter when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new HTMLToPDFConverter();
});
