/**
 * Common handler for pages selection radio buttons
 * Works with radio buttons pattern: pagesAll, pagesCurrent, pagesCustom, pagesCustomInput
 */

document.addEventListener('DOMContentLoaded', () => {
    // Find all pages selector groups
    const pagesSelectors = [
        { prefix: 'rotate', currentPageVar: null },
        { prefix: 'remove', currentPageVar: null },
        { prefix: 'pageNumbers', currentPageVar: null },
        { prefix: 'pages', currentPageVar: 'currentPage' }, // For crop_pdf
        { prefix: 'watermarkPages', currentPageVar: 'currentPage' }, // For watermark
    ];

    pagesSelectors.forEach(({ prefix, currentPageVar }) => {
        const allRadio = document.getElementById(`${prefix}PagesAll`) || 
                        document.getElementById(`${prefix}All`);
        const currentRadio = document.getElementById(`${prefix}PagesCurrent`) || 
                            document.getElementById(`${prefix}Current`);
        const customRadio = document.getElementById(`${prefix}PagesCustom`) || 
                           document.getElementById(`${prefix}Custom`);
        const customInput = document.getElementById(`${prefix}PagesCustomInput`) || 
                           document.getElementById(`${prefix}CustomInput`);
        const hiddenPagesInput = document.getElementById('pages');

        if (!allRadio && !currentRadio && !customRadio) {
            return; // This selector group doesn't exist
        }

        // Handler for "All pages"
        if (allRadio) {
            allRadio.addEventListener('change', () => {
                if (customInput) {
                    customInput.disabled = true;
                    customInput.value = '';
                    customInput.removeAttribute('required');
                }
                if (hiddenPagesInput) {
                    hiddenPagesInput.value = 'all';
                }
            });
        }

        // Handler for "Current page only"
        if (currentRadio) {
            currentRadio.addEventListener('change', () => {
                if (customInput) {
                    customInput.disabled = true;
                    customInput.value = '';
                    customInput.removeAttribute('required');
                }
                // Get current page from page selector or default to 1
                let currentPage = 1;
                if (currentPageVar && window[currentPageVar]) {
                    currentPage = window[currentPageVar];
                } else {
                    const pageSelector = document.getElementById('pageSelector');
                    if (pageSelector) {
                        currentPage = parseInt(pageSelector.value) || 1;
                    }
                }
                if (hiddenPagesInput) {
                    hiddenPagesInput.value = currentPage.toString();
                }
            });
        }

        // Handler for "Custom pages"
        if (customRadio && customInput) {
            customRadio.addEventListener('change', () => {
                customInput.disabled = false;
                customInput.focus();
                if (customInput.hasAttribute('data-required')) {
                    customInput.setAttribute('required', 'required');
                }
            });
        }

        // Update hidden input when custom input changes
        if (customInput && hiddenPagesInput) {
            customInput.addEventListener('input', () => {
                if (!customInput.disabled && customInput.value.trim()) {
                    hiddenPagesInput.value = customInput.value.trim();
                }
            });
        }
    });

    // Handle form submission - update hidden pages field based on radio selection
    document.addEventListener('submit', (e) => {
        const form = e.target;
        if (form.tagName !== 'FORM') return;

        // Find the active pages selector group
        const allRadios = form.querySelectorAll('input[name="pagesOption"]');
        if (allRadios.length === 0) {
            return; // No pages selector in this form
        }

        const hiddenPagesInput = form.querySelector('input[name="pages"][type="hidden"]');
        if (!hiddenPagesInput) {
            return;
        }

        // Find which radio is checked
        let checkedRadio = null;
        allRadios.forEach(radio => {
            if (radio.checked) {
                checkedRadio = radio;
            }
        });

        if (!checkedRadio) {
            // Default to "all" if nothing is checked
            hiddenPagesInput.value = 'all';
            return;
        }

        const radioId = checkedRadio.id;
        let pagesValue = 'all';

        if (radioId.includes('All') || radioId.endsWith('All')) {
            pagesValue = 'all';
        } else if (radioId.includes('Current') || radioId.endsWith('Current')) {
            // Get current page
            let currentPage = 1;
            const pageSelector = form.querySelector('#pageSelector');
            if (pageSelector) {
                currentPage = parseInt(pageSelector.value) || 1;
            } else if (window.currentPage) {
                currentPage = window.currentPage;
            }
            pagesValue = currentPage.toString();
        } else if (radioId.includes('Custom') || radioId.endsWith('Custom')) {
            // Get custom input value - try different selectors
            const prefix = radioId.replace('PagesCustom', '').replace('Custom', '');
            let customInput = form.querySelector(`#${prefix}PagesCustomInput`);
            if (!customInput) {
                customInput = form.querySelector(`#${prefix}CustomInput`);
            }
            if (!customInput) {
                customInput = form.querySelector('input[name="pagesCustom"]');
            }
            if (customInput && customInput.value.trim()) {
                pagesValue = customInput.value.trim();
            } else {
                // For remove pages, if custom is selected but empty, don't submit
                if (radioId.includes('remove')) {
                    e.preventDefault();
                    alert(window.ENTER_PAGE_NUMBERS || 'Please enter page numbers to remove, or select "All pages" or "Current page only"');
                    return;
                }
                pagesValue = 'all'; // Fallback
            }
        }

        hiddenPagesInput.value = pagesValue;
    }, true); // Use capture phase to ensure it runs before other handlers
});

