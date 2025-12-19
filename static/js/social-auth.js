class SocialAuth {
    constructor() {
        this.popup = null;
        this.checkInterval = null;
    }

    openPopup(provider, url) {
        console.log('Opening popup for provider:', provider, 'url:', url);

        const width = 500;
        const height = 600;
        const left = (screen.width / 2) - (width / 2);
        const top = (screen.height / 2) - (height / 2);

        this.popup = window.open(
            url,
            `social_auth_${provider}`,
            `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
        );

        if (!this.popup) {
            console.error('Popup blocked by browser');
            return;
        }

        console.log('Popup opened successfully');
        // Show loading indicator
        this.showLoading(provider);

        // Start checking for popup close
        this.startPolling(provider);
    }

    showLoading(provider) {
        const button = document.querySelector(`[data-provider="${provider}"]`);
        if (button) {
            const originalContent = button.innerHTML;
            button.innerHTML = `
                <div class="flex items-center justify-center">
                    <svg class="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0112 20c5.522 0 9.533-2.312 11.709-5.291L16 17.709V12z"></path>
                    </svg>
                    <span>Авторизация...</span>
                </div>
            `;
            button.disabled = true;

            // Store original content to restore later
            button.dataset.originalContent = originalContent;
        }
    }

    hideLoading(provider) {
        const button = document.querySelector(`[data-provider="${provider}"]`);
        if (button && button.dataset.originalContent) {
            button.innerHTML = button.dataset.originalContent;
            button.disabled = false;
        }
    }

    startPolling(provider) {
        console.log('Starting polling for provider:', provider);
        this.checkInterval = setInterval(() => {
            if (!this.popup || this.popup.closed) {
                console.log('Popup closed or null');
                this.stopPolling();
                this.hideLoading(provider);
                return;
            }

            try {
                // Check if popup has been redirected to our callback
                if (this.popup.location.hostname === window.location.hostname) {
                    console.log('Popup redirected to our domain');
                    this.stopPolling();
                    this.handleCallback(provider);
                }
            } catch (e) {
                // Cross-origin error - popup still on Google domain
                // This is normal, continue polling
                console.log('Cross-origin error (normal):', e.message);
            }
        }, 1000);
    }

    stopPolling() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    handleCallback(provider) {
        try {
            const url = new URL(this.popup.location.href);
            console.log('Handling callback URL:', url.href);

            const params = new URLSearchParams(url.search);

            // Check for success or error
            if (params.has('code') || params.has('access_token')) {
                console.log('OAuth success detected');
                // Success - close popup and redirect
                this.popup.close();
                window.location.href = url.toString();
            } else if (params.has('error')) {
                console.log('OAuth error:', params.get('error'));
                // Error - show message
                this.popup.close();
                this.showError(provider, params.get('error'));
            }
        } catch (e) {
            console.error('Error handling OAuth callback:', e);
            this.popup.close();
            this.showError(provider, 'unknown_error');
        }
    }

    showError(provider, error) {
        const errorMessage = {
            'access_denied': 'Доступ запрещен',
            'redirect_uri_mismatch': 'Неверный redirect URI',
            'unknown_error': 'Произошла ошибка'
        }[error] || 'Произошла ошибка авторизации';

        console.error('Social auth error:', error, errorMessage);

        // Show error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'mb-4 p-3 rounded-lg bg-red-100 text-red-700';
        errorDiv.innerHTML = errorMessage;

        const form = document.querySelector('form');
        if (form) {
            form.parentNode.insertBefore(errorDiv, form);

            // Remove error after 5 seconds
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }
    }
}

// Initialize social auth
const socialAuth = new SocialAuth();

// Add click handlers to social buttons
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing social auth');

    const googleButton = document.querySelector('[data-provider="google"]');
    const facebookButton = document.querySelector('[data-provider="facebook"]');

    console.log('Found buttons:', { googleButton, facebookButton });

    if (googleButton) {
        googleButton.addEventListener('click', function(e) {
            console.log('Google button clicked');
            e.preventDefault();
            socialAuth.openPopup('google', this.href);
        });
    }

    if (facebookButton) {
        facebookButton.addEventListener('click', function(e) {
            console.log('Facebook button clicked');
            e.preventDefault();
            socialAuth.openPopup('facebook', this.href);
        });
    }
});
