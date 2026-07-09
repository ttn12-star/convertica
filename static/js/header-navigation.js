/**
 * Header Navigation Component
 * Handles mobile menu, mega menu, and responsive navigation
 */
class HeaderNavigation {
  constructor() {
    this.header = document.querySelector('header');
    this.mobileBtn = document.getElementById('mobile-menu-btn');
    this.mobileMenu = document.getElementById('mobile-menu');
    this.megaParent = document.getElementById('mega-menu-parent');
    this.megaDropdown = document.getElementById('mega-menu-dropdown');
    this.megaButton = document.getElementById('mega-menu-button');
    this.megaArrow = document.getElementById('mega-menu-arrow');
    this.mobileMegaToggle = document.getElementById('mobile-mega-toggle');
    this.mobileMegaMenu = document.getElementById('mobile-mega-menu');
    this.editPdfParent = document.getElementById('edit-pdf-menu-parent');
    this.editPdfDropdown = document.getElementById('edit-pdf-menu-dropdown');
    this.editPdfButton = document.getElementById('edit-pdf-menu-button');
    this.editPdfArrow = document.getElementById('edit-pdf-menu-arrow');
    this.organizePdfParent = document.getElementById('organize-pdf-menu-parent');
    this.organizePdfDropdown = document.getElementById('organize-pdf-menu-dropdown');
    this.organizePdfButton = document.getElementById('organize-pdf-menu-button');
    this.organizePdfArrow = document.getElementById('organize-pdf-menu-arrow');
    this.premiumToolsParent = document.getElementById('premium-tools-menu-parent');
    this.premiumToolsDropdown = document.getElementById('premium-tools-menu-dropdown');
    this.premiumToolsButton = document.getElementById('premium-tools-menu-button');
    this.premiumToolsArrow = document.getElementById('premium-tools-menu-arrow');
    this.imagesParent = document.getElementById('images-menu-parent');
    this.imagesDropdown = document.getElementById('images-menu-dropdown');
    this.imagesButton = document.getElementById('images-menu-button');
    this.imagesArrow = document.getElementById('images-menu-arrow');
    this.mobileImagesToggle = document.getElementById('mobile-images-toggle');
    this.mobileImagesMenu = document.getElementById('mobile-images-menu');
    this.mobileEditPdfToggle = document.getElementById('mobile-edit-pdf-toggle');
    this.mobileEditPdfMenu = document.getElementById('mobile-edit-pdf-menu');
    this.mobileOrganizePdfToggle = document.getElementById('mobile-organize-pdf-toggle');
    this.mobileOrganizePdfMenu = document.getElementById('mobile-organize-pdf-menu');
    this.mobilePdfSecurityToggle = document.getElementById('mobile-pdf-security-toggle');
    this.mobilePdfSecurityMenu = document.getElementById('mobile-pdf-security-menu');
    this.mobileArchiveToolsToggle = document.getElementById('mobile-archive-tools-toggle');
    this.mobileArchiveToolsMenu = document.getElementById('mobile-archive-tools-menu');
    this.mobilePremiumToggle = document.getElementById('mobile-premium-toggle');
    this.mobilePremiumMenu = document.getElementById('mobile-premium-menu');
    this.allToolsParent = document.getElementById('all-tools-menu-parent');
    this.allToolsDropdown = document.getElementById('all-tools-menu-dropdown');
    this.allToolsButton = document.getElementById('all-tools-menu-button');
    this.allToolsArrow = document.getElementById('all-tools-menu-arrow');
    this.moreParent = document.getElementById('more-menu-parent');
    this.moreDropdown = document.getElementById('more-menu-dropdown');
    this.moreButton = document.getElementById('more-menu-button');
    this.moreArrow = document.getElementById('more-menu-arrow');
    // Mobile More menu
    this.mobileMoreToggle = document.getElementById('mobile-more-toggle');
    this.mobileMoreMenu = document.getElementById('mobile-more-menu');
    // Mobile All Tools is now a simple link, no toggle needed
    this.menuIconOpen = document.getElementById('menu-icon-open');
    this.menuIconClose = document.getElementById('menu-icon-close');

    // Priority+ overflow nav
    this.rowEl = this.header?.querySelector('.container > div');
    this.leftCluster = this.rowEl?.querySelector(':scope > div');
    this.navEl = document.querySelector('header nav[aria-label]');
    this.moreToolsParent = document.getElementById('more-tools-menu-parent');
    this.moreToolsButton = document.getElementById('more-tools-menu-button');
    this.moreToolsDropdown = document.getElementById('more-tools-menu-dropdown');
    this.moreToolsSlots = document.getElementById('more-tools-menu-slots');
    this.moreToolsArrow = document.getElementById('more-tools-menu-arrow');
    // Category menus that may collapse into the bucket, in visual (DOM) order.
    // Drop order (first to overflow) is the reverse: Premium → … → Convert.
    this.overflowCategories = [
      'mega-menu-parent', 'edit-pdf-menu-parent', 'organize-pdf-menu-parent',
      'images-menu-parent', 'premium-tools-menu-parent',
    ].map((id) => document.getElementById(id)).filter(Boolean);
    this._pendingRaf = null;

    this.init();
  }

  init() {
    // Mobile menu toggle
    this.mobileBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleMobile();
    });

    // Desktop mega menu (hover) - always attach, check width in methods
    if (this.megaParent) {
      this.megaParent.addEventListener('mouseenter', () => this.showMega());
      this.megaParent.addEventListener('mouseleave', () => this.hideMega());
    }

    // Desktop mega menu (click for accessibility)
    this.megaButton?.addEventListener('click', (e) => {
      if (window.innerWidth < 768) {
        e.preventDefault();
        this.toggleMegaDesktop();
      }
    });

    // Mobile mega menu toggle
    this.mobileMegaToggle?.addEventListener('click', () => this.toggleMobileMega());

    // Desktop edit PDF menu (hover) - always attach, check width in methods
    if (this.editPdfParent) {
      this.editPdfParent.addEventListener('mouseenter', () => this.showEditPdf());
      this.editPdfParent.addEventListener('mouseleave', () => this.hideEditPdf());
    }

    // Desktop edit PDF menu (click for accessibility)
    this.editPdfButton?.addEventListener('click', (e) => {
      if (window.innerWidth < 768) {
        e.preventDefault();
        this.toggleEditPdfDesktop();
      }
    });

    // Desktop organize PDF menu (hover) - always attach, check width in methods
    if (this.organizePdfParent) {
      this.organizePdfParent.addEventListener('mouseenter', () => this.showOrganizePdf());
      this.organizePdfParent.addEventListener('mouseleave', () => this.hideOrganizePdf());
    }

    // Desktop organize PDF menu (click for accessibility)
    this.organizePdfButton?.addEventListener('click', (e) => {
      if (window.innerWidth < 768) {
        e.preventDefault();
        this.toggleOrganizePdfDesktop();
      }
    });

    // Desktop premium tools menu (hover) - always attach, check width in methods
    if (this.premiumToolsParent) {
      this.premiumToolsParent.addEventListener('mouseenter', () => this.showPremiumTools());
      this.premiumToolsParent.addEventListener('mouseleave', () => this.hidePremiumTools());
    }

    // Desktop premium tools menu (click for accessibility)
    this.premiumToolsButton?.addEventListener('click', (e) => {
      if (window.innerWidth >= 768) {
        e.preventDefault();
        this.togglePremiumToolsDesktop();
      }
    });

    // Desktop images menu (hover) - always attach, check width in methods
    if (this.imagesParent) {
      this.imagesParent.addEventListener('mouseenter', () => this.showImages());
      this.imagesParent.addEventListener('mouseleave', () => this.hideImages());
    }

    // Desktop images menu (click for accessibility)
    this.imagesButton?.addEventListener('click', (e) => {
      if (window.innerWidth < 768) {
        e.preventDefault();
        this.toggleImagesDesktop();
      }
    });

    // Mobile images menu toggle
    this.mobileImagesToggle?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleMobileImages();
    });

    // Mobile organize PDF menu toggle
    this.mobileEditPdfToggle?.addEventListener('click', () => this.toggleMobileEditPdf());
    this.mobileOrganizePdfToggle?.addEventListener('click', () => this.toggleMobileOrganizePdf());
    this.mobilePdfSecurityToggle?.addEventListener('click', () => this.toggleMobilePdfSecurity());
    this.mobileArchiveToolsToggle?.addEventListener('click', () => this.toggleMobileArchiveTools());
    this.mobilePremiumToggle?.addEventListener('click', () => this.toggleMobilePremium());

    // Desktop all tools menu (hover) - always attach, check width in methods
    if (this.allToolsParent) {
      this.allToolsParent.addEventListener('mouseenter', () => this.showAllTools());
      this.allToolsParent.addEventListener('mouseleave', () => this.hideAllTools());
    }

    // Desktop all tools menu (click for accessibility and to prevent navigation)
    this.allToolsButton?.addEventListener('click', (e) => {
      // On desktop, prevent navigation and toggle dropdown instead
      if (window.innerWidth >= 768) {
        e.preventDefault();
        this.toggleAllToolsDesktop();
      }
      // On mobile, allow navigation (it's a simple link)
    });

    // Desktop more menu (hover) - always attach, check width in methods
    if (this.moreParent) {
      this.moreParent.addEventListener('mouseenter', () => this.showMore());
      this.moreParent.addEventListener('mouseleave', () => this.hideMore());
    }

    // Desktop more menu (click for accessibility)
    this.moreButton?.addEventListener('click', (e) => {
      if (window.innerWidth < 768) {
        e.preventDefault();
        this.toggleMoreDesktop();
      }
    });

    // Mobile all tools menu toggle
    // Mobile All Tools is now a simple link, no event listener needed

    // Mobile more menu toggle
    this.mobileMoreToggle?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleMobileMore();
    });

    // Close menus on outside click
    document.addEventListener('click', (e) => this.outsideClick(e));

    // Close any open menu on Escape and return focus to its trigger (WCAG
    // 2.1.2 — keyboard users must be able to dismiss the dropdowns/menus).
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' || e.key === 'Esc') this.closeAllMenus();
    });

    // Handle window resize
    window.addEventListener('resize', () => this.handleResize());

    // --- Priority+ overflow nav ---
    // Bucket trigger (hover + click), mirrors the other desktop menus.
    if (this.moreToolsParent) {
      this.moreToolsParent.addEventListener('mouseenter', () => this.showMoreTools());
      this.moreToolsParent.addEventListener('mouseleave', () => this.hideMoreTools());
    }
    this.moreToolsButton?.addEventListener('click', (e) => {
      e.preventDefault();
      this.toggleMoreToolsDesktop();
    });
    // When a category lives in the bucket, its trigger toggles an accordion
    // instead of the normal dropdown. Capture-phase so it wins over the
    // category's own click handler without editing that handler.
    this.overflowCategories.forEach((cat) => {
      const btn = cat.querySelector(':scope > button');
      if (!btn) return;
      btn.addEventListener('click', (e) => {
        if (cat.classList.contains('nav-overflowed')) {
          e.preventDefault();
          e.stopImmediatePropagation();
          this.toggleAccordion(cat);
        }
      }, true);
    });
    // Recompute what fits whenever the row OR the nav's own box resizes
    // (rAF-debounced). Observing the nav matters at breakpoints/font swaps:
    // those change the nav's content width without changing the row width, so
    // a row-only observer would miss them. recomputeOverflow is idempotent for
    // a given width, so our own item moves settle in one extra cycle (no loop).
    if (window.ResizeObserver) {
      this._ro = new ResizeObserver(() => this.scheduleOverflowRecompute());
      // Observe every element whose width feeds the collision test: the row
      // (viewport), the nav content, the "All Tools" button (its label toggles
      // at the lg breakpoint) and the logo (font swap). A breakpoint/font change
      // can widen All Tools or the logo without changing the row or nav width,
      // so observing only the row would miss it. None of these are resized by
      // our own item moves, so there is no observer feedback loop.
      const logo = this.header?.querySelector('a[itemprop="url"]');
      [this.rowEl, this.navEl, this.allToolsParent, logo].forEach((el) => {
        if (el) this._ro.observe(el);
      });
    }
    this.scheduleOverflowRecompute();
    // Belt-and-suspenders for late reflows (fonts, icons, breakpoint styles)
    // that a ResizeObserver might not attribute to an observed element.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => this.scheduleOverflowRecompute());
    }
    window.addEventListener('load', () => this.scheduleOverflowRecompute());
    [150, 500, 1000].forEach((t) => setTimeout(() => this.scheduleOverflowRecompute(), t));
  }

  closeAllMenus() {
    // Desktop dropdowns
    this.hideMega();
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hideAllTools();
    this.hidePremiumTools();
    this.hideImages();
    this.hideMore();
    this.hideMoreTools();
    // Mobile slide-out menu
    if (this.mobileMenu && !this.mobileMenu.classList.contains('hidden')) {
      this.mobileMenu.classList.add('hidden');
      this.mobileBtn?.setAttribute('aria-expanded', 'false');
      if (this.menuIconOpen && this.menuIconClose) {
        this.menuIconOpen.classList.remove('hidden');
        this.menuIconClose.classList.add('hidden');
      }
      this.mobileBtn?.focus();
    }
  }

  toggleMobile() {
    if (!this.mobileMenu || !this.mobileBtn) return;
    const isOpen = !this.mobileMenu.classList.contains('hidden');

    // Update menu position before showing
    if (isOpen) {
      // Closing menu
      this.mobileMenu.classList.add('hidden');
    } else {
      // Opening menu - position it below the header
      this.updateMobileMenuPosition();
      this.mobileMenu.classList.remove('hidden');
    }

    this.mobileBtn.setAttribute('aria-expanded', !isOpen);

    // Toggle menu icon
    if (this.menuIconOpen && this.menuIconClose) {
      if (isOpen) {
        this.menuIconOpen.classList.remove('hidden');
        this.menuIconClose.classList.add('hidden');
      } else {
        this.menuIconOpen.classList.add('hidden');
        this.menuIconClose.classList.remove('hidden');
      }
    }
  }

  updateMobileMenuPosition() {
    if (!this.mobileMenu || !this.header) return;
    const headerHeight = this.header.offsetHeight;
    this.mobileMenu.style.top = `${headerHeight}px`;
    this.mobileMenu.style.maxHeight = `calc(100vh - ${headerHeight}px)`;
  }

  showMega() {
    if (window.innerWidth < 768) return;
    if (this.megaParent?.classList.contains('nav-overflowed')) return;
    if (!this.megaDropdown || !this.megaParent || !this.megaButton) return;
    // Hide other menus if open
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hideAllTools();
    this.hidePremiumTools();
    this.hideImages();
    this.megaDropdown.classList.remove('opacity-0', 'invisible');
    this.megaDropdown.classList.add('opacity-100', 'visible');
    this.megaParent.setAttribute('aria-expanded', 'true');
    this.megaButton.setAttribute('aria-expanded', 'true');
    if (this.megaArrow) {
      this.megaArrow.classList.add('rotate-180');
    }
  }

  hideMega() {
    if (window.innerWidth < 768) return;
    if (this.megaParent?.classList.contains('nav-overflowed')) return;
    if (!this.megaDropdown || !this.megaParent || !this.megaButton) return;
    this.megaDropdown.classList.remove('opacity-100', 'visible');
    this.megaDropdown.classList.add('opacity-0', 'invisible');
    this.megaParent.setAttribute('aria-expanded', 'false');
    this.megaButton.setAttribute('aria-expanded', 'false');
    if (this.megaArrow) {
      this.megaArrow.classList.remove('rotate-180');
    }
  }

  toggleMegaDesktop() {
    const isVisible = !this.megaDropdown.classList.contains('invisible');
    isVisible ? this.hideMega() : this.showMega();
  }

  toggleMobileMega() {
    if (!this.mobileMegaToggle || !this.mobileMegaMenu) return;
    const isExpanded = this.mobileMegaToggle.getAttribute('aria-expanded') === 'true';
    this.mobileMegaMenu.classList.toggle('hidden', isExpanded);
    this.mobileMegaToggle.setAttribute('aria-expanded', !isExpanded);

    // Rotate arrow icon
    const arrow = this.mobileMegaToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  showEditPdf() {
    if (window.innerWidth < 768) return;
    if (this.editPdfParent?.classList.contains('nav-overflowed')) return;
    if (!this.editPdfDropdown || !this.editPdfParent || !this.editPdfButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideOrganizePdf();
    this.hideAllTools();
    this.hidePremiumTools();
    this.hideImages();
    this.editPdfDropdown.classList.remove('opacity-0', 'invisible');
    this.editPdfDropdown.classList.add('opacity-100', 'visible');
    this.editPdfParent.setAttribute('aria-expanded', 'true');
    this.editPdfButton.setAttribute('aria-expanded', 'true');
    if (this.editPdfArrow) {
      this.editPdfArrow.classList.add('rotate-180');
    }
  }

  hideEditPdf() {
    if (window.innerWidth < 768) return;
    if (this.editPdfParent?.classList.contains('nav-overflowed')) return;
    if (!this.editPdfDropdown || !this.editPdfParent || !this.editPdfButton) return;
    this.editPdfDropdown.classList.remove('opacity-100', 'visible');
    this.editPdfDropdown.classList.add('opacity-0', 'invisible');
    this.editPdfParent.setAttribute('aria-expanded', 'false');
    this.editPdfButton.setAttribute('aria-expanded', 'false');
    if (this.editPdfArrow) {
      this.editPdfArrow.classList.remove('rotate-180');
    }
  }

  toggleEditPdfDesktop() {
    if (!this.editPdfDropdown) return;
    const isVisible = !this.editPdfDropdown.classList.contains('invisible');
    isVisible ? this.hideEditPdf() : this.showEditPdf();
  }

  toggleMobileEditPdf() {
    if (!this.mobileEditPdfToggle || !this.mobileEditPdfMenu) return;

    const isExpanded = this.mobileEditPdfToggle.getAttribute('aria-expanded') === 'true';
    this.mobileEditPdfMenu.classList.toggle('hidden', isExpanded);
    this.mobileEditPdfToggle.setAttribute('aria-expanded', !isExpanded);

    const arrow = this.mobileEditPdfToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  showOrganizePdf() {
    if (window.innerWidth < 768) return;
    if (this.organizePdfParent?.classList.contains('nav-overflowed')) return;
    if (!this.organizePdfDropdown || !this.organizePdfParent || !this.organizePdfButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideEditPdf();
    this.hideAllTools();
    this.hidePremiumTools();
    this.hideImages();
    this.organizePdfDropdown.classList.remove('opacity-0', 'invisible');
    this.organizePdfDropdown.classList.add('opacity-100', 'visible');
    this.organizePdfParent.setAttribute('aria-expanded', 'true');
    this.organizePdfButton.setAttribute('aria-expanded', 'true');
    if (this.organizePdfArrow) {
      this.organizePdfArrow.classList.add('rotate-180');
    }
  }

  hideOrganizePdf() {
    if (window.innerWidth < 768) return;
    if (this.organizePdfParent?.classList.contains('nav-overflowed')) return;
    if (!this.organizePdfDropdown || !this.organizePdfParent || !this.organizePdfButton) return;
    this.organizePdfDropdown.classList.remove('opacity-100', 'visible');
    this.organizePdfDropdown.classList.add('opacity-0', 'invisible');
    this.organizePdfParent.setAttribute('aria-expanded', 'false');
    this.organizePdfButton.setAttribute('aria-expanded', 'false');
    if (this.organizePdfArrow) {
      this.organizePdfArrow.classList.remove('rotate-180');
    }
  }

  toggleOrganizePdfDesktop() {
    if (!this.organizePdfDropdown) return;
    const isVisible = !this.organizePdfDropdown.classList.contains('invisible');
    isVisible ? this.hideOrganizePdf() : this.showOrganizePdf();
  }

  toggleMobileOrganizePdf() {
    if (!this.mobileOrganizePdfToggle || !this.mobileOrganizePdfMenu) return;
    const isExpanded = this.mobileOrganizePdfToggle.getAttribute('aria-expanded') === 'true';
    this.mobileOrganizePdfMenu.classList.toggle('hidden', isExpanded);
    this.mobileOrganizePdfToggle.setAttribute('aria-expanded', !isExpanded);

    // Rotate arrow icon
    const arrow = this.mobileOrganizePdfToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  toggleMobilePdfSecurity() {
    if (!this.mobilePdfSecurityToggle || !this.mobilePdfSecurityMenu) return;
    const isExpanded = this.mobilePdfSecurityToggle.getAttribute('aria-expanded') === 'true';
    this.mobilePdfSecurityMenu.classList.toggle('hidden', isExpanded);
    this.mobilePdfSecurityToggle.setAttribute('aria-expanded', !isExpanded);

    // Rotate arrow icon
    const arrow = this.mobilePdfSecurityToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  toggleMobileArchiveTools() {
    if (!this.mobileArchiveToolsToggle || !this.mobileArchiveToolsMenu) return;
    const isExpanded = this.mobileArchiveToolsToggle.getAttribute('aria-expanded') === 'true';
    this.mobileArchiveToolsMenu.classList.toggle('hidden', isExpanded);
    this.mobileArchiveToolsToggle.setAttribute('aria-expanded', !isExpanded);

    // Rotate arrow icon
    const arrow = this.mobileArchiveToolsToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  toggleMobilePremium() {
    if (!this.mobilePremiumToggle || !this.mobilePremiumMenu) return;
    const isExpanded = this.mobilePremiumToggle.getAttribute('aria-expanded') === 'true';
    this.mobilePremiumMenu.classList.toggle('hidden', isExpanded);
    this.mobilePremiumToggle.setAttribute('aria-expanded', !isExpanded);

    // Rotate the chevron (not the leading lightning icon)
    const arrow = this.mobilePremiumToggle.querySelector('.mobile-premium-arrow');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  toggleMobileMore() {
    if (!this.mobileMoreToggle || !this.mobileMoreMenu) return;
    const isExpanded = this.mobileMoreToggle.getAttribute('aria-expanded') === 'true';
    this.mobileMoreMenu.classList.toggle('hidden', isExpanded);
    this.mobileMoreToggle.setAttribute('aria-expanded', !isExpanded);

    // Rotate arrow icon
    const arrow = this.mobileMoreToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  showAllTools() {
    if (window.innerWidth < 768) return;
    if (!this.allToolsDropdown || !this.allToolsParent || !this.allToolsButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hidePremiumTools();
    this.hideImages();

    // Position menu to expand from button center
    const buttonRect = this.allToolsButton.getBoundingClientRect();
    const dropdownWidth = Math.min(1400, window.innerWidth - 32);
    const leftPosition = buttonRect.left + (buttonRect.width / 2) - (dropdownWidth / 2);
    const clampedLeft = Math.max(16, Math.min(leftPosition, window.innerWidth - dropdownWidth - 16));
    const topPosition = buttonRect.bottom + 8; // 8px = mt-2 (0.5rem)

    this.allToolsDropdown.style.position = 'fixed';
    this.allToolsDropdown.style.left = `${clampedLeft}px`;
    this.allToolsDropdown.style.top = `${topPosition}px`;
    this.allToolsDropdown.style.transform = 'translateX(0)';
    this.allToolsDropdown.style.width = `${dropdownWidth}px`;

    this.allToolsDropdown.classList.remove('opacity-0', 'invisible');
    this.allToolsDropdown.classList.add('opacity-100', 'visible');
    this.allToolsParent.setAttribute('aria-expanded', 'true');
    this.allToolsButton.setAttribute('aria-expanded', 'true');
    if (this.allToolsArrow) {
      this.allToolsArrow.classList.add('rotate-180');
    }
  }

  hideAllTools() {
    if (window.innerWidth < 768) return;
    if (!this.allToolsDropdown || !this.allToolsParent || !this.allToolsButton) return;
    this.allToolsDropdown.classList.remove('opacity-100', 'visible');
    this.allToolsDropdown.classList.add('opacity-0', 'invisible');
    this.allToolsParent.setAttribute('aria-expanded', 'false');
    this.allToolsButton.setAttribute('aria-expanded', 'false');
    if (this.allToolsArrow) {
      this.allToolsArrow.classList.remove('rotate-180');
    }
  }

  toggleAllToolsDesktop() {
    if (!this.allToolsDropdown) return;
    const isVisible = !this.allToolsDropdown.classList.contains('invisible');
    isVisible ? this.hideAllTools() : this.showAllTools();
  }

  showImages() {
    if (window.innerWidth < 768) return;
    if (this.imagesParent?.classList.contains('nav-overflowed')) return;
    if (!this.imagesDropdown || !this.imagesParent || !this.imagesButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hideAllTools();
    this.hidePremiumTools();
    this.hideMore();
    this.imagesDropdown.classList.remove('opacity-0', 'invisible');
    this.imagesDropdown.classList.add('opacity-100', 'visible');
    this.imagesParent.setAttribute('aria-expanded', 'true');
    this.imagesButton.setAttribute('aria-expanded', 'true');
    if (this.imagesArrow) {
      this.imagesArrow.classList.add('rotate-180');
    }
  }

  hideImages() {
    if (window.innerWidth < 768) return;
    if (this.imagesParent?.classList.contains('nav-overflowed')) return;
    if (!this.imagesDropdown || !this.imagesParent || !this.imagesButton) return;
    this.imagesDropdown.classList.remove('opacity-100', 'visible');
    this.imagesDropdown.classList.add('opacity-0', 'invisible');
    this.imagesParent.setAttribute('aria-expanded', 'false');
    this.imagesButton.setAttribute('aria-expanded', 'false');
    if (this.imagesArrow) {
      this.imagesArrow.classList.remove('rotate-180');
    }
  }

  toggleImagesDesktop() {
    if (!this.imagesDropdown) return;
    const isVisible = !this.imagesDropdown.classList.contains('invisible');
    isVisible ? this.hideImages() : this.showImages();
  }

  toggleMobileImages() {
    if (!this.mobileImagesToggle || !this.mobileImagesMenu) return;
    const isExpanded = this.mobileImagesToggle.getAttribute('aria-expanded') === 'true';
    this.mobileImagesMenu.classList.toggle('hidden', isExpanded);
    this.mobileImagesToggle.setAttribute('aria-expanded', !isExpanded);

    // Rotate arrow icon
    const arrow = this.mobileImagesToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  showPremiumTools() {
    if (window.innerWidth < 768) return;
    if (this.premiumToolsParent?.classList.contains('nav-overflowed')) return;
    if (!this.premiumToolsDropdown || !this.premiumToolsParent || !this.premiumToolsButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hideAllTools();
    this.hideImages();
    this.hideMore();
    this.premiumToolsDropdown.classList.remove('opacity-0', 'invisible');
    this.premiumToolsDropdown.classList.add('opacity-100', 'visible');
    this.premiumToolsParent.setAttribute('aria-expanded', 'true');
    this.premiumToolsButton.setAttribute('aria-expanded', 'true');
    if (this.premiumToolsArrow) {
      this.premiumToolsArrow.classList.add('rotate-180');
    }
  }

  hidePremiumTools() {
    if (window.innerWidth < 768) return;
    if (this.premiumToolsParent?.classList.contains('nav-overflowed')) return;
    if (!this.premiumToolsDropdown || !this.premiumToolsParent || !this.premiumToolsButton) return;
    this.premiumToolsDropdown.classList.remove('opacity-100', 'visible');
    this.premiumToolsDropdown.classList.add('opacity-0', 'invisible');
    this.premiumToolsParent.setAttribute('aria-expanded', 'false');
    this.premiumToolsButton.setAttribute('aria-expanded', 'false');
    if (this.premiumToolsArrow) {
      this.premiumToolsArrow.classList.remove('rotate-180');
    }
  }

  togglePremiumToolsDesktop() {
    if (!this.premiumToolsDropdown) return;
    const isVisible = !this.premiumToolsDropdown.classList.contains('invisible');
    isVisible ? this.hidePremiumTools() : this.showPremiumTools();
  }

  showMore() {
    if (window.innerWidth < 768) return;
    if (!this.moreDropdown || !this.moreParent || !this.moreButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hideAllTools();
    this.hidePremiumTools();
    this.hideImages();
    this.moreDropdown.classList.remove('opacity-0', 'invisible');
    this.moreDropdown.classList.add('opacity-100', 'visible');
    this.moreParent.setAttribute('aria-expanded', 'true');
    this.moreButton.setAttribute('aria-expanded', 'true');
    if (this.moreArrow) {
      this.moreArrow.classList.add('rotate-180');
    }
  }

  hideMore() {
    if (window.innerWidth < 768) return;
    if (!this.moreDropdown || !this.moreParent || !this.moreButton) return;
    this.moreDropdown.classList.remove('opacity-100', 'visible');
    this.moreDropdown.classList.add('opacity-0', 'invisible');
    this.moreParent.setAttribute('aria-expanded', 'false');
    this.moreButton.setAttribute('aria-expanded', 'false');
    if (this.moreArrow) {
      this.moreArrow.classList.remove('rotate-180');
    }
  }

  toggleMoreDesktop() {
    if (!this.moreDropdown) return;
    const isVisible = !this.moreDropdown.classList.contains('invisible');
    isVisible ? this.hideMore() : this.showMore();
  }

  // toggleMobileAllTools removed - mobile All Tools is now a simple link

  outsideClick(e) {
    // Close mobile menu
    if (this.mobileMenu &&
        !this.mobileMenu.classList.contains('hidden') &&
        !this.mobileMenu.contains(e.target) &&
        !this.mobileBtn.contains(e.target)) {
      this.mobileMenu.classList.add('hidden');
      this.mobileBtn.setAttribute('aria-expanded', 'false');
      if (this.menuIconOpen && this.menuIconClose) {
        this.menuIconOpen.classList.remove('hidden');
        this.menuIconClose.classList.add('hidden');
      }
    }

    // Close mobile more menu
    if (this.mobileMoreMenu &&
        !this.mobileMoreMenu.classList.contains('hidden') &&
        !this.mobileMoreMenu.contains(e.target) &&
        !this.mobileMoreToggle.contains(e.target)) {
      this.mobileMoreMenu.classList.add('hidden');
      this.mobileMoreToggle.setAttribute('aria-expanded', 'false');
      const arrow = this.mobileMoreToggle.querySelector('svg');
      if (arrow) {
        arrow.classList.remove('rotate-180');
      }
    }

    // Close desktop mega menu
    if (this.megaDropdown &&
        !this.megaParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hideMega();
    }

    // Close desktop edit PDF menu
    if (this.editPdfDropdown &&
        !this.editPdfParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hideEditPdf();
    }

    // Close desktop organize PDF menu
    if (this.organizePdfDropdown &&
        !this.organizePdfParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hideOrganizePdf();
    }

    // Close desktop all tools menu
    if (this.allToolsDropdown &&
        !this.allToolsParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hideAllTools();
    }

    // Close desktop premium tools menu
    if (this.premiumToolsDropdown &&
        !this.premiumToolsParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hidePremiumTools();
    }

    // Close desktop images menu
    if (this.imagesDropdown &&
        this.imagesParent &&
        !this.imagesParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hideImages();
    }

    // Close desktop more menu
    if (this.moreDropdown &&
        !this.moreParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hideMore();
    }

    // Close desktop More tools bucket
    if (this.moreToolsDropdown &&
        this.moreToolsParent &&
        !this.moreToolsParent.contains(e.target) &&
        window.innerWidth >= 768) {
      this.hideMoreTools();
    }
  }

  handleResize() {
    // Hide mega menu on mobile
    if (window.innerWidth < 768) {
      this.hideMega();
      this.hideEditPdf();
      this.hideOrganizePdf();
      this.hideAllTools();
      this.hidePremiumTools();
      this.hideImages();
      this.hideMore();
    }

    // Update mobile menu position if it's open
    if (this.mobileMenu && !this.mobileMenu.classList.contains('hidden')) {
      this.updateMobileMenuPosition();
    }

    // Recompute Priority+ overflow after a width change.
    this.scheduleOverflowRecompute();
  }

  // ---- Priority+ overflow bucket ("More tools") ----

  showMoreTools() {
    if (window.innerWidth < 768) return;
    if (!this.moreToolsDropdown || !this.moreToolsParent || !this.moreToolsButton) return;
    this.hideMega();
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hideAllTools();
    this.hidePremiumTools();
    this.hideImages();
    this.hideMore();
    this.moreToolsDropdown.classList.remove('opacity-0', 'invisible');
    this.moreToolsDropdown.classList.add('opacity-100', 'visible');
    this.moreToolsParent.setAttribute('aria-expanded', 'true');
    this.moreToolsButton.setAttribute('aria-expanded', 'true');
    this.moreToolsArrow?.classList.add('rotate-180');
  }

  hideMoreTools() {
    if (window.innerWidth < 768) return;
    if (!this.moreToolsDropdown || !this.moreToolsParent || !this.moreToolsButton) return;
    this.moreToolsDropdown.classList.remove('opacity-100', 'visible');
    this.moreToolsDropdown.classList.add('opacity-0', 'invisible');
    this.moreToolsParent.setAttribute('aria-expanded', 'false');
    this.moreToolsButton.setAttribute('aria-expanded', 'false');
    this.moreToolsArrow?.classList.remove('rotate-180');
  }

  toggleMoreToolsDesktop() {
    if (!this.moreToolsDropdown) return;
    const isVisible = !this.moreToolsDropdown.classList.contains('invisible');
    isVisible ? this.hideMoreTools() : this.showMoreTools();
  }

  // Accordion inside the bucket for a collapsed category.
  toggleAccordion(cat) {
    const dd = cat.querySelector(':scope > [id$="-menu-dropdown"]');
    if (!dd) return;
    const isOpen = !dd.classList.contains('hidden');
    dd.classList.toggle('hidden', isOpen);
    cat.classList.toggle('open', !isOpen);
    const btn = cat.querySelector(':scope > button');
    btn?.setAttribute('aria-expanded', String(!isOpen));
  }

  _makeAccordion(cat) {
    cat.classList.add('nav-overflowed');
    cat.classList.remove('open');
    const dd = cat.querySelector(':scope > [id$="-menu-dropdown"]');
    dd?.classList.add('hidden');
  }

  _unmakeAccordion(cat) {
    cat.classList.remove('nav-overflowed', 'open');
    const dd = cat.querySelector(':scope > [id$="-menu-dropdown"]');
    if (dd) {
      dd.classList.remove('hidden', 'opacity-100', 'visible');
      dd.classList.add('opacity-0', 'invisible');
    }
    cat.querySelector(':scope > button')?.setAttribute('aria-expanded', 'false');
  }

  // Does the nav physically collide with the "All Tools" button? The nav lives
  // in a flex-1 wrapper and, when too wide, overflows toward All Tools — that is
  // the visible collision. getBoundingClientRect is direction-agnostic (RTL ok).
  _navCollides() {
    const anchor = this.allToolsParent || this.leftCluster;
    if (!anchor || !this.navEl) return false;
    const a = anchor.getBoundingClientRect();
    const b = this.navEl.getBoundingClientRect();
    if (a.width === 0 || b.width === 0) return false;
    const GAP = 8;
    const overlap = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    return overlap > -GAP;
  }

  _resetCategoriesHome() {
    // Move any overflowed category back into the bar, before the bucket,
    // in visual order (so the original order is preserved).
    this.overflowCategories.forEach((cat) => {
      if (cat.parentElement === this.moreToolsSlots) {
        this._unmakeAccordion(cat);
        this.navEl.insertBefore(cat, this.moreToolsParent);
      }
    });
  }

  _moveToOverflow(cat) {
    this._makeAccordion(cat);
    this.moreToolsSlots.appendChild(cat);
  }

  scheduleOverflowRecompute() {
    if (this._pendingRaf) return;
    this._pendingRaf = requestAnimationFrame(() => {
      this._pendingRaf = null;
      this.recomputeOverflow();
    });
  }

  recomputeOverflow() {
    if (!this.navEl || !this.moreToolsParent || !this.moreToolsSlots) return;

    // Remember which accordions the user had expanded, so a later recompute
    // (resize, font swap, settle tick) doesn't collapse them under the user.
    const openIds = new Set(
      this.overflowCategories.filter((c) => c.classList.contains('open')).map((c) => c.id),
    );

    // Always start from the fully-expanded bar.
    this._resetCategoriesHome();
    this.moreToolsParent.classList.add('hidden');

    // Below md the mobile hamburger owns navigation.
    if (window.innerWidth < 768) return;

    // Drop from the right until the bar no longer collides with the logo cluster.
    const dropOrder = this.overflowCategories.slice().reverse();
    let moved = 0;
    for (const cat of dropOrder) {
      if (!this._navCollides()) break;
      if (moved === 0) this.moreToolsParent.classList.remove('hidden');
      this._moveToOverflow(cat);
      moved += 1;
    }

    if (moved === 0) {
      this.moreToolsParent.classList.add('hidden');
      return;
    }
    // Re-order the bucket contents into natural (visual) order top-to-bottom,
    // and restore any accordion the user had expanded before this recompute.
    this.overflowCategories.forEach((cat) => {
      if (cat.parentElement !== this.moreToolsSlots) return;
      this.moreToolsSlots.appendChild(cat);
      if (openIds.has(cat.id)) {
        cat.querySelector(':scope > [id$="-menu-dropdown"]')?.classList.remove('hidden');
        cat.classList.add('open');
      }
    });
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.headerNavigation = new HeaderNavigation();
});
