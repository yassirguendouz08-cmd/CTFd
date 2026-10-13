(() => {
  const nav = document.getElementById('theme-navigation');
  const menu = document.querySelector('.cd-menu-toggle');
  const accountButton = document.getElementById('accountDropdownToggle');
  const accountMenu = document.getElementById('accountDropdown');
  const closeAccount = () => {
    if (accountMenu) accountMenu.hidden = true;
    accountButton?.setAttribute('aria-expanded', 'false');
  };
  const closeNav = () => {
    nav?.classList.remove('mobile-open');
    menu?.setAttribute('aria-expanded', 'false');
  };
  menu?.addEventListener('click', () => {
    const open = nav.classList.toggle('mobile-open');
    menu.setAttribute('aria-expanded', String(open));
    if (open) nav.querySelector('a')?.focus();
  });
  accountButton?.addEventListener('click', () => {
    const open = accountMenu.hidden;
    accountMenu.hidden = !open;
    accountButton.setAttribute('aria-expanded', String(open));
    if (open) accountMenu.querySelector('a')?.focus();
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.cd-account')) closeAccount();
    if (!event.target.closest('.cd-header')) closeNav();
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (accountMenu && !accountMenu.hidden) { closeAccount(); accountButton?.focus(); }
    else if (nav?.classList.contains('mobile-open')) { closeNav(); menu?.focus(); }
  });
  matchMedia('(min-width: 1200px)').addEventListener('change', closeNav);
  nav?.querySelectorAll('a.cd-nav-link').forEach(link => {
    const path = new URL(link.href, location.href).pathname;
    if (path === location.pathname || (path !== '/' && location.pathname.startsWith(path + '/'))) link.setAttribute('aria-current', 'page');
  });
})();
