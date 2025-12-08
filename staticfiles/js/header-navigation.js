/**
 * Header Navigation Component
 * Handles mobile menu, mega menu, and responsive navigation
 */
class HeaderNavigation {
  constructor() {
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
    this.mobileOrganizePdfToggle = document.getElementById('mobile-organize-pdf-toggle');
    this.mobileOrganizePdfMenu = document.getElementById('mobile-organize-pdf-menu');
    this.mobilePdfSecurityToggle = document.getElementById('mobile-pdf-security-toggle');
    this.mobilePdfSecurityMenu = document.getElementById('mobile-pdf-security-menu');
    this.allToolsParent = document.getElementById('all-tools-menu-parent');
    this.allToolsDropdown = document.getElementById('all-tools-menu-dropdown');
    this.allToolsButton = document.getElementById('all-tools-menu-button');
    this.allToolsArrow = document.getElementById('all-tools-menu-arrow');
    this.mobileAllToolsToggle = document.getElementById('mobile-all-tools-toggle');
    this.mobileAllToolsMenu = document.getElementById('mobile-all-tools-menu');
    this.menuIconOpen = document.getElementById('menu-icon-open');
    this.menuIconClose = document.getElementById('menu-icon-close');

    this.init();
  }

  init() {
    // Mobile menu toggle
    this.mobileBtn?.addEventListener('click', () => this.toggleMobile());
    
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

    // Mobile organize PDF menu toggle
    this.mobileOrganizePdfToggle?.addEventListener('click', () => this.toggleMobileOrganizePdf());
    this.mobilePdfSecurityToggle?.addEventListener('click', () => this.toggleMobilePdfSecurity());

    // Desktop all tools menu (hover) - always attach, check width in methods
    if (this.allToolsParent) {
      this.allToolsParent.addEventListener('mouseenter', () => this.showAllTools());
      this.allToolsParent.addEventListener('mouseleave', () => this.hideAllTools());
    }

    // Mobile all tools menu toggle
    this.mobileAllToolsToggle?.addEventListener('click', () => this.toggleMobileAllTools());

    // Close menus on outside click
    document.addEventListener('click', (e) => this.outsideClick(e));

    // Handle window resize
    window.addEventListener('resize', () => this.handleResize());
  }

  toggleMobile() {
    if (!this.mobileMenu || !this.mobileBtn) return;
    const isOpen = !this.mobileMenu.classList.contains('hidden');
    this.mobileMenu.classList.toggle('hidden', isOpen);
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

  showMega() {
    if (window.innerWidth < 768) return;
    if (!this.megaDropdown || !this.megaParent || !this.megaButton) return;
    // Hide other menus if open
    this.hideEditPdf();
    this.hideOrganizePdf();
    this.hideAllTools();
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
    if (!this.editPdfDropdown || !this.editPdfParent || !this.editPdfButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideOrganizePdf();
    this.hideAllTools();
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

  showOrganizePdf() {
    if (window.innerWidth < 768) return;
    if (!this.organizePdfDropdown || !this.organizePdfParent || !this.organizePdfButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideEditPdf();
    this.hideAllTools();
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

  showAllTools() {
    if (window.innerWidth < 768) return;
    if (!this.allToolsDropdown || !this.allToolsParent || !this.allToolsButton) return;
    // Hide other menus if open
    this.hideMega();
    this.hideEditPdf();
    this.hideOrganizePdf();
    
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

  toggleMobileAllTools() {
    if (!this.mobileAllToolsToggle || !this.mobileAllToolsMenu) return;
    const isExpanded = this.mobileAllToolsToggle.getAttribute('aria-expanded') === 'true';
    this.mobileAllToolsMenu.classList.toggle('hidden', isExpanded);
    this.mobileAllToolsToggle.setAttribute('aria-expanded', !isExpanded);
    
    // Rotate arrow icon
    const arrow = this.mobileAllToolsToggle.querySelector('svg');
    if (arrow) {
      arrow.classList.toggle('rotate-180');
    }
  }

  outsideClick(e) {
    // Close mobile menu
    if (this.mobileMenu && 
        !this.mobileMenu.contains(e.target) && 
        !this.mobileBtn.contains(e.target)) {
      this.mobileMenu.classList.add('hidden');
      this.mobileBtn.setAttribute('aria-expanded', 'false');
      if (this.menuIconOpen && this.menuIconClose) {
        this.menuIconOpen.classList.remove('hidden');
        this.menuIconClose.classList.add('hidden');
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
  }

  handleResize() {
    // Hide mega menu on mobile
    if (window.innerWidth < 768) {
      this.hideMega();
      this.hideEditPdf();
      this.hideOrganizePdf();
      this.hideAllTools();
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.headerNavigation = new HeaderNavigation();
});
