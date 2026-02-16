document.addEventListener('DOMContentLoaded', function() {
    // Update page limit message based on user status
    const freeUserNote = document.getElementById('freeUserNote');
    const premiumUserNote = document.getElementById('premiumUserNote');

    // Simple check - if premium elements exist, user is premium
    var isPremium = document.querySelector('[data-premium="true"]') !== null;

    if (isPremium) {
        if (premiumUserNote) premiumUserNote.classList.remove('hidden');
        if (freeUserNote) freeUserNote.classList.add('hidden');
    } else {
        if (freeUserNote) freeUserNote.classList.remove('hidden');
        if (premiumUserNote) premiumUserNote.classList.add('hidden');

        // Add upgrade link for free users
        const upgradeLink = document.createElement('div');
        upgradeLink.className = 'mt-2';
        upgradeLink.innerHTML = '<a href="/pricing/" class="text-sm text-amber-600 hover:text-amber-700 font-medium">Get Premium from $1/day →</a>';

        // Insert after the note
        if (freeUserNote && !freeUserNote.querySelector('.mt-2')) {
            freeUserNote.appendChild(upgradeLink);
        }
    }

    // OCR Language Selection Toggle (only for premium users)
    const ocrEnabled = document.getElementById('ocrEnabled');
    const ocrLanguageSection = document.getElementById('ocrLanguageSection');
    const ocrLanguageSelect = document.getElementById('ocrLanguage');
    const query = new URLSearchParams(window.location.search);
    const shouldEnableOcrFromQuery = ['1', 'true', 'yes', 'on'].includes((query.get('ocr') || '').toLowerCase());
    const requestedOcrLanguage = (query.get('ocr_lang') || '').trim().toLowerCase();

    console.log('OCR Debug: ocrEnabled found:', !!ocrEnabled);
    console.log('OCR Debug: ocrLanguageSection found:', !!ocrLanguageSection);
    console.log('OCR Debug: ocrLanguageSelect found:', !!ocrLanguageSelect);

    // Only proceed if language section exists (premium users only)
    if (ocrEnabled && ocrLanguageSection && ocrLanguageSelect) {
        console.log('OCR Debug: All elements found, setting up event listener');

        // Show/hide language selection based on OCR checkbox
        function updateLanguageVisibility() {
            if (ocrEnabled.checked) {
                ocrLanguageSection.style.opacity = '1';
                ocrLanguageSection.style.pointerEvents = 'auto';
                ocrLanguageSelect.disabled = false;
                console.log('OCR Debug: Language section enabled');
            } else {
                ocrLanguageSection.style.opacity = '0.5';
                ocrLanguageSection.style.pointerEvents = 'none';
                ocrLanguageSelect.disabled = true;
                console.log('OCR Debug: Language section disabled');
            }
        }

        ocrEnabled.addEventListener('change', updateLanguageVisibility);

        if (shouldEnableOcrFromQuery && !ocrEnabled.disabled) {
            ocrEnabled.checked = true;
        }

        if (requestedOcrLanguage && !ocrLanguageSelect.disabled) {
            const hasRequestedLanguage = Array.from(ocrLanguageSelect.options).some(
                (option) => option.value.toLowerCase() === requestedOcrLanguage
            );
            if (hasRequestedLanguage) {
                ocrLanguageSelect.value = requestedOcrLanguage;
            }
        }

        // Set initial state after optional query presets
        updateLanguageVisibility();
    } else {
        console.log('OCR Debug: OCR language selection not available (user not premium)');
    }
});
