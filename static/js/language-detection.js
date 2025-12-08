/**
 * Language detection helper for Convertica
 *
 * Note: Server-side AutoLanguageMiddleware already handles automatic language
 * detection from Accept-Language header and saves it to session.
 *
 * This script is minimal and mainly for logging/debugging purposes.
 * The actual detection happens on the server side via LocaleMiddleware
 * and AutoLanguageMiddleware.
 */
(function() {
    'use strict';

    // Server-side middleware handles everything automatically
    // This script can be used for future enhancements if needed
    // For now, language detection is fully handled server-side

    // Optional: Log detected language for debugging
    if (typeof console !== 'undefined' && console.debug) {
        const htmlLang = document.documentElement.lang || 'en';
        const browserLang = (navigator.language || navigator.userLanguage || 'en').split('-')[0].toLowerCase();
        console.debug('Language detection:', {
            pageLanguage: htmlLang,
            browserLanguage: browserLang,
            match: htmlLang === browserLang
        });
    }
})();
