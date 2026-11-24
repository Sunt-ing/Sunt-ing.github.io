(() => {
  const root = document.documentElement;
  const button = document.querySelector('.theme');
  const refresh = () => { const dark = root.dataset.theme === 'dark'; button.textContent = dark ? '☀' : '◐'; button.setAttribute('aria-pressed', String(dark)); };
  refresh();
  button.addEventListener('click', () => { root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; try { localStorage.setItem('ting-theme', root.dataset.theme); } catch {} refresh(); document.dispatchEvent(new CustomEvent('ting-theme-change', {detail: root.dataset.theme})); });
  const headings = [...document.querySelectorAll('.prose h2[id]')];
  if (headings.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => { for (const entry of entries) if (entry.isIntersecting) document.querySelectorAll('.toc a').forEach(a => a.classList.toggle('active', a.hash === '#' + entry.target.id)); }, {rootMargin:'-80px 0px -60% 0px'});
    headings.forEach(h => observer.observe(h));
  }
})();
