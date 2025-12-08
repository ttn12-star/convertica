/**
 * Cookie Consent Utility
 * Helper functions to check and use cookie consent preferences in the project
 */

/**
 * Get cookie consent status
 * @returns {Object} Consent status object
 */
function getCookieConsent() {
    const consent = localStorage.getItem('cookie_consent');
    const analytics = localStorage.getItem('cookie_analytics') === 'true';
    const marketing = localStorage.getItem('cookie_marketing') === 'true';
    const consentDate = localStorage.getItem('cookie_consent_date');

    return {
        consent: consent, // 'accepted', 'rejected', 'custom', or null
        analytics: analytics,
        marketing: marketing,
        consentDate: consentDate ? new Date(consentDate) : null,
        hasConsented: consent !== null
    };
}

/**
 * Check if analytics cookies are allowed
 * @returns {boolean}
 */
function isAnalyticsAllowed() {
    const consent = getCookieConsent();
    return consent.analytics === true;
}

/**
 * Check if marketing cookies are allowed
 * @returns {boolean}
 */
function isMarketingAllowed() {
    const consent = getCookieConsent();
    return consent.marketing === true;
}

/**
 * Check if user has given consent
 * @returns {boolean}
 */
function hasUserConsented() {
    const consent = getCookieConsent();
    return consent.hasConsented;
}

/**
 * Initialize analytics (e.g., Google Analytics) only if allowed
 * @param {Function} initFunction - Function to initialize analytics
 */
function initAnalyticsIfAllowed(initFunction) {
    if (isAnalyticsAllowed()) {
        if (typeof initFunction === 'function') {
            initFunction();
        } else if (typeof window.gtag !== 'undefined') {
            // Example for Google Analytics
            window.gtag('consent', 'update', {
                'analytics_storage': 'granted'
            });
        }
    } else {
        // Disable analytics
        if (typeof window.gtag !== 'undefined') {
            window.gtag('consent', 'update', {
                'analytics_storage': 'denied'
            });
        }
    }
}

/**
 * Initialize marketing scripts only if allowed
 * @param {Function} initFunction - Function to initialize marketing
 */
function initMarketingIfAllowed(initFunction) {
    if (isMarketingAllowed()) {
        if (typeof initFunction === 'function') {
            initFunction();
        }
        // Example: Enable Facebook Pixel, Google Ads, etc.
    } else {
        // Disable marketing scripts
        // Example: Disable tracking pixels
    }
}

/**
 * Track page view (only if analytics is allowed)
 * @param {string} page - Page path
 */
function trackPageView(page) {
    if (isAnalyticsAllowed()) {
        // Example for Google Analytics
        if (typeof window.gtag !== 'undefined') {
            window.gtag('config', 'GA_MEASUREMENT_ID', {
                'page_path': page
            });
        }
        // Add other analytics tracking here
        console.log('Page view tracked:', page);
    }
}

/**
 * Track event (only if analytics is allowed)
 * @param {string} eventName - Event name
 * @param {Object} eventData - Event data
 */
function trackEvent(eventName, eventData) {
    if (isAnalyticsAllowed()) {
        // Example for Google Analytics
        if (typeof window.gtag !== 'undefined') {
            window.gtag('event', eventName, eventData);
        }
        // Add other analytics tracking here
        console.log('Event tracked:', eventName, eventData);
    }
}

// Listen for cookie consent changes
window.addEventListener('cookieConsentAccepted', function(event) {
    console.log('Cookie consent accepted:', event.detail);
    initAnalyticsIfAllowed();
    initMarketingIfAllowed();
});

window.addEventListener('cookieConsentRejected', function(event) {
    console.log('Cookie consent rejected:', event.detail);
    // Analytics and marketing are already disabled
});

window.addEventListener('cookieConsentUpdated', function(event) {
    console.log('Cookie consent updated:', event.detail);
    initAnalyticsIfAllowed();
    initMarketingIfAllowed();
});

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.CookieConsent = {
        getCookieConsent: getCookieConsent,
        isAnalyticsAllowed: isAnalyticsAllowed,
        isMarketingAllowed: isMarketingAllowed,
        hasUserConsented: hasUserConsented,
        initAnalyticsIfAllowed: initAnalyticsIfAllowed,
        initMarketingIfAllowed: initMarketingIfAllowed,
        trackPageView: trackPageView,
        trackEvent: trackEvent
    };
}
