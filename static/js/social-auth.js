class SocialAuth {
    constructor() {
        // No popup needed - use standard redirect
    }

    openAuth(provider, url) {
        // Show loading indicator
        this.showLoading(provider);

        // Standard redirect to OAuth provider
        window.location.href = url;
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
                    <span>Authorizing...</span>
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

}

// Initialize social auth
const socialAuth = new SocialAuth();

// Add click handlers to social buttons
document.addEventListener('DOMContentLoaded', function() {
    const googleButton = document.querySelector('[data-provider="google"]');
    const facebookButton = document.querySelector('[data-provider="facebook"]');

    if (googleButton) {
        googleButton.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            socialAuth.openAuth('google', url);
        });
    }

    if (facebookButton) {
        facebookButton.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            socialAuth.openAuth('facebook', url);
        });
    }
});
