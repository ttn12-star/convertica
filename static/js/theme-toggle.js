/**
 * Premium Dark Theme Toggle
 * Manages theme switching for premium users with localStorage persistence
 */

(function() {
    'use strict';

    const THEME_KEY = 'convertica_theme';
    const THEME_LIGHT = 'light';
    const THEME_DARK = 'dark';

    class ThemeManager {
        constructor() {
            this.isPremium = document.documentElement.dataset.isPremium === 'true';
            const storedTheme = this.getStoredTheme();
            this.currentTheme = this.isPremium ? (storedTheme || THEME_LIGHT) : THEME_LIGHT;
            this.init();
        }

        init() {
            // Apply theme immediately to prevent flash
            // Non-premium users must never have dark mode applied (even if localStorage contains "dark")
            this.applyTheme(this.currentTheme, false);

            // Setup toggle button for everyone:
            // - premium: toggles theme
            // - non-premium: opens premium modal
            this.setupToggleButton();

            // Listen for system theme changes
            if (window.matchMedia) {
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                    if (!this.isPremium) {
                        return;
                    }
                    if (!this.getStoredTheme()) {
                        this.applyTheme(e.matches ? THEME_DARK : THEME_LIGHT);
                    }
                });
            }
        }

        getStoredTheme() {
            try {
                return localStorage.getItem(THEME_KEY);
            } catch (e) {
                return null;
            }
        }

        setStoredTheme(theme) {
            try {
                localStorage.setItem(THEME_KEY, theme);
            } catch (e) {
                console.warn('Failed to save theme preference:', e);
            }
        }

        applyTheme(theme, animate = true) {
            const html = document.documentElement;
            const body = document.body;

            // Hard gate: only premium users can ever apply dark mode.
            // If a non-premium user somehow reaches here with "dark", force light.
            if (!this.isPremium && theme === THEME_DARK) {
                theme = THEME_LIGHT;
            }

            if (theme === THEME_DARK) {
                html.classList.add('dark');
                body.classList.add('dark-mode');
            } else {
                html.classList.remove('dark');
                body.classList.remove('dark-mode');
            }

            this.currentTheme = theme;
            this.setStoredTheme(theme);
            this.updateToggleButton();

            // Dispatch event for other components
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
        }

        toggleTheme() {
            console.log('Toggle theme clicked. isPremium:', this.isPremium);

            if (!this.isPremium) {
                console.log('Showing premium modal');
                this.showPremiumModal();
                return;
            }

            const newTheme = this.currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
            this.applyTheme(newTheme);
        }

        setupToggleButton() {
            const button = document.getElementById('theme-toggle-btn');
            if (!button) return;

            button.addEventListener('click', () => this.toggleTheme());
            this.updateToggleButton();
        }

        updateToggleButton() {
            const button = document.getElementById('theme-toggle-btn');
            if (!button) return;

            const icon = button.querySelector('.theme-icon');
            const isDark = this.currentTheme === THEME_DARK;

            if (icon) {
                icon.innerHTML = isDark
                    ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>'
                    : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>';
            }

            button.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            button.setAttribute('title', isDark ? 'Light Mode' : 'Dark Mode');
        }

        showPremiumModal() {
            // Show premium upgrade modal
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in';
            modal.innerHTML = `
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-6 animate-scale-in">
                    <div class="flex items-center justify-center w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-amber-500 to-orange-600 rounded-full">
                        <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path>
                        </svg>
                    </div>
                    <h3 class="text-2xl font-bold text-center mb-2 text-gray-900 dark:text-white">Premium Feature</h3>
                    <p class="text-center text-gray-600 dark:text-gray-300 mb-6">
                        Dark theme is available exclusively for Premium users. Upgrade now to enjoy this and many other premium features!
                    </p>
                    <div class="flex gap-3">
                        <button onclick="this.closest('.fixed').remove()" class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300 font-medium">
                            Maybe Later
                        </button>
                        <a href="/pricing/" class="flex-1 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-600 text-white rounded-lg hover:from-amber-600 hover:to-orange-700 transition-all font-bold text-center">
                            Upgrade Now
                        </a>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Close on backdrop click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
        }
    }

    // Initialize theme manager when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new ThemeManager());
    } else {
        new ThemeManager();
    }

    // Export for external access
    window.ThemeManager = ThemeManager;
})();
