class HeaderNavigation {
  constructor() {
    this.mobileBtn = document.getElementById('mobile-menu-btn');
    this.mobileMenu = document.getElementById('mobile-menu');
    this.megaParent = document.getElementById('mega-menu-parent');
    this.megaDropdown = document.getElementById('mega-menu-dropdown');
    this.megaButton = document.getElementById('mega-menu-button');
    this.megaArrow = document.getElementById('mega-menu-arrow');

    this.init();
  }

  init() {
    this.mobileBtn?.addEventListener('click', () => this.toggleMobile());
    document.addEventListener('click', (e) => this.outsideClick(e));

    this.megaParent?.addEventListener('mouseenter', () => this.showMega());
    this.megaParent?.addEventListener('mouseleave', () => this.hideMega());
    this.megaButton?.addEventListener('click', (e) => this.toggleMegaMobile(e));
  }

  toggleMobile() {
    const isOpen = !this.mobileMenu.classList.contains('hidden');
    this.mobileMenu.classList.toggle('hidden', isOpen);
    this.mobileBtn.setAttribute('aria-expanded', !isOpen);
  }

  showMega() {
    this.megaDropdown.classList.remove('opacity-0', 'invisible');
    this.megaDropdown.classList.add('opacity-100', 'visible');
    this.megaParent.setAttribute('aria-expanded', 'true');
    this.megaArrow.classList.add('rotate-180');
  }

  hideMega() {
    this.megaDropdown.classList.remove('opacity-100', 'visible');
    this.megaDropdown.classList.add('opacity-0', 'invisible');
    this.megaParent.setAttribute('aria-expanded', 'false');
    this.megaArrow.classList.remove('rotate-180');
  }

  toggleMegaMobile(e) {
    e.preventDefault();
    if (window.innerWidth < 768) return;
    const isVisible = !this.megaDropdown.classList.contains('invisible');
    isVisible ? this.hideMega() : this.showMega();
  }

  outsideClick(e) {
    if (this.mobileMenu && !this.mobileMenu.contains(e.target) && !this.mobileBtn.contains(e.target)) {
      this.mobileMenu.classList.add('hidden');
      this.mobileBtn.setAttribute('aria-expanded', 'false');
    }
    if (this.megaDropdown && !this.megaParent.contains(e.target)) {
      this.hideMega();
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.headerNavigation = new HeaderNavigation();
});
