/**
 * PWA Install Prompt Handler
 * Shows custom install prompt for "Add to Home Screen"
 */

class PWAInstaller {
    constructor() {
        this.deferredPrompt = null;
        this.installButton = null;
        this.isInstalled = false;
        this.dismissed = false;
        this.isLinuxDesktop = false;

        this.init();
    }

    init() {
        // Respect user dismissal for 7 days
        try {
            const dismissedUntil = Number(localStorage.getItem('pwa-install-dismissed') || 0);
            if (dismissedUntil && Date.now() < dismissedUntil) {
                this.dismissed = true;
            }
        } catch (e) {
        }

        // Check if already installed
        if (window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true) {
            this.isInstalled = true;
            console.log('[PWA] App is already installed');
            return;
        }

        // Listen for beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('[PWA] Install prompt available');

            try {
                const ua = (navigator.userAgent || '');
                const platform = (navigator.platform || '');
                const isAndroid = /Android/i.test(ua);
                const isIOS = /iPhone|iPad|iPod/i.test(ua);
                const isLinux = /Linux/i.test(platform) || /Linux/i.test(ua);
                this.isLinuxDesktop = Boolean(isLinux && !isAndroid);

                // Custom banner is intended for mobile "Add to Home Screen".
                // On desktop, rely on native browser UI to avoid confusing installs
                // (e.g. untrusted .desktop launchers on some Linux desktops).
                const isMobile = Boolean(isAndroid || isIOS);
                if (!isMobile) {
                    return;
                }
            } catch (err) {
                this.isLinuxDesktop = false;
            }

            if (this.isLinuxDesktop) {
                return;
            }

            // Prevent default browser prompt
            e.preventDefault();

            // Store the event for later use
            this.deferredPrompt = e;

            // Show custom install button
            if (!this.dismissed) {
                this.showInstallButton();
            }
        });

        // Listen for app installed event
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed successfully');
            this.isInstalled = true;
            this.hideInstallButton();

            // Track installation
            if (typeof gtag !== 'undefined') {
                gtag('event', 'pwa_install', {
                    event_category: 'engagement',
                    event_label: 'PWA Installed'
                });
            }
        });

        // Check if service worker is supported
        if ('serviceWorker' in navigator) {
            this.registerServiceWorker();
        }
    }

    async registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js', {
                scope: '/'
            });

            console.log('[PWA] Service Worker registered:', registration.scope);

            // Check for updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                console.log('[PWA] Service Worker update found');

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // New service worker available
                        this.showUpdateNotification();
                    }
                });
            });

        } catch (error) {
            console.error('[PWA] Service Worker registration failed:', error);
        }
    }

    showInstallButton() {
        // Check if install button already exists
        if (document.getElementById('pwa-install-button')) {
            return;
        }

        // Create install button
        const installBanner = document.createElement('div');
        installBanner.id = 'pwa-install-banner';
        installBanner.className = 'fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-md bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg shadow-2xl p-4 z-50 transform transition-all duration-300 ease-in-out';
        installBanner.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="flex-shrink-0">
                    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                    </svg>
                </div>
                <div class="flex-1 min-w-0">
                    <h3 class="text-sm font-semibold mb-1">Install Convertica</h3>
                    <p class="text-xs opacity-90 mb-3">Add to your home screen for quick access and offline support!</p>
                    <div class="flex gap-2">
                        <button id="pwa-install-button" class="px-4 py-2 bg-white text-blue-600 rounded-md text-sm font-medium hover:bg-gray-100 transition-colors">
                            Install
                        </button>
                        <button id="pwa-install-dismiss" class="px-4 py-2 bg-transparent border border-white/30 rounded-md text-sm font-medium hover:bg-white/10 transition-colors">
                            Not now
                        </button>
                    </div>
                </div>
                <button id="pwa-install-close" class="flex-shrink-0 text-white/70 hover:text-white transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(installBanner);

        // Add event listeners
        document.getElementById('pwa-install-button').addEventListener('click', () => {
            this.promptInstall();
        });

        document.getElementById('pwa-install-dismiss').addEventListener('click', () => {
            this.hideInstallButton();
            // Remember user dismissed (for 7 days)
            localStorage.setItem('pwa-install-dismissed', Date.now() + (7 * 24 * 60 * 60 * 1000));
        });

        document.getElementById('pwa-install-close').addEventListener('click', () => {
            this.hideInstallButton();
        });

        // Animate in
        setTimeout(() => {
            installBanner.style.transform = 'translateY(0)';
        }, 100);
    }

    hideInstallButton() {
        const banner = document.getElementById('pwa-install-banner');
        if (banner) {
            banner.style.transform = 'translateY(150%)';
            setTimeout(() => {
                banner.remove();
            }, 300);
        }
    }

    async promptInstall() {
        if (!this.deferredPrompt) {
            console.log('[PWA] Install prompt not available');
            return;
        }

        // Show the install prompt
        this.deferredPrompt.prompt();

        // Wait for the user's response
        const { outcome } = await this.deferredPrompt.userChoice;
        console.log('[PWA] User choice:', outcome);

        if (outcome === 'accepted') {
            console.log('[PWA] User accepted the install prompt');

            // Track acceptance
            if (typeof gtag !== 'undefined') {
                gtag('event', 'pwa_install_accepted', {
                    event_category: 'engagement'
                });
            }
        } else {
            console.log('[PWA] User dismissed the install prompt');

            // Track dismissal
            if (typeof gtag !== 'undefined') {
                gtag('event', 'pwa_install_dismissed', {
                    event_category: 'engagement'
                });
            }
        }

        // Clear the deferred prompt
        this.deferredPrompt = null;

        // Hide the install button
        this.hideInstallButton();
    }

    showUpdateNotification() {
        // Show notification that new version is available
        const updateBanner = document.createElement('div');
        updateBanner.id = 'pwa-update-banner';
        updateBanner.className = 'fixed top-4 left-4 right-4 md:left-auto md:right-4 md:max-w-md bg-green-600 text-white rounded-lg shadow-2xl p-4 z-50';
        updateBanner.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="flex-shrink-0">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                </div>
                <div class="flex-1">
                    <h3 class="text-sm font-semibold mb-1">Update Available</h3>
                    <p class="text-xs opacity-90 mb-2">A new version of Convertica is available!</p>
                    <button id="pwa-update-button" class="px-4 py-1.5 bg-white text-green-600 rounded-md text-sm font-medium hover:bg-gray-100 transition-colors">
                        Reload to Update
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(updateBanner);

        document.getElementById('pwa-update-button').addEventListener('click', () => {
            window.location.reload();
        });
    }

    // Request notification permission
    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('[PWA] Notifications not supported');
            return false;
        }

        if (Notification.permission === 'granted') {
            return true;
        }

        if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            return permission === 'granted';
        }

        return false;
    }

    // Show notification (for testing)
    async showNotification(title, options = {}) {
        const hasPermission = await this.requestNotificationPermission();

        if (!hasPermission) {
            console.log('[PWA] Notification permission denied');
            return;
        }

        const registration = await navigator.serviceWorker.ready;

        await registration.showNotification(title, {
            body: options.body || 'Your conversion is complete!',
            icon: options.icon || '/static/favicon-192x192.png',
            badge: options.badge || '/static/favicon-96x96.png',
            tag: options.tag || 'convertica-notification',
            requireInteraction: options.requireInteraction || false,
            data: options.data || {},
            ...options
        });
    }
}

// Initialize PWA installer when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaInstaller = new PWAInstaller();
    });
} else {
    window.pwaInstaller = new PWAInstaller();
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.PWAInstaller = PWAInstaller;
}
