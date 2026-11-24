// Offline preview only: srcdoc has no independent URL, so route explicitly.
(() => {
  document.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link || event.defaultPrevented) return;
    const href = link.getAttribute('href');
    if (!href) return;
    if (href.startsWith('/') || href.startsWith('#')) {
      event.preventDefault();
      parent.postMessage({type: 'preview-route', path: href}, '*');
    }
  });
  document.querySelectorAll('a[href^="https://"],a[href^="http://"],a[href^="mailto:"]').forEach(link => {
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
  });
  document.addEventListener('ting-theme-change', event => {
    parent.postMessage({type: 'preview-theme', theme: event.detail}, '*');
  });
  window.addEventListener('message', event => {
    if (event.source !== parent || event.data?.type !== 'preview-init') return;
    if (event.data.theme === 'dark' || event.data.theme === 'light') {
      const dark = event.data.theme === 'dark';
      document.documentElement.dataset.theme = event.data.theme;
      const button = document.querySelector('.theme');
      if (button) { button.textContent = dark ? '☀' : '◐'; button.setAttribute('aria-pressed', String(dark)); }
    }
    if (!event.data.hash) window.scrollTo(0, 0);
    if (event.data.hash) {
      const target = document.getElementById(event.data.hash);
      if (target) {
        target.scrollIntoView();
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({preventScroll:true});
      }
    }
  });
  parent.postMessage({type: 'preview-ready'}, '*');
})();
