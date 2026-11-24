// The packager defines `pages` before this script.
const frame = document.querySelector('iframe');
let currentRoute = '';
let targetHash = '';
let previewTheme = null;
function routeFromHash() {
  try { return decodeURIComponent(location.hash.slice(1)) || '/'; }
  catch { return '/'; }
}
function initializeFrame() {
  frame.contentWindow.postMessage({type:'preview-init', theme:previewTheme, hash:targetHash}, '*');
}
function show(path) {
  const hashIndex = path.indexOf('#');
  const route = hashIndex < 0 ? path : path.slice(0, hashIndex);
  try { targetHash = hashIndex < 0 ? '' : decodeURIComponent(path.slice(hashIndex + 1)); }
  catch { targetHash = ''; }
  const next = Object.hasOwn(pages, route) ? route : '/';
  if (currentRoute === next) { initializeFrame(); return; }
  currentRoute = next;
  frame.srcdoc = pages[next];
}
window.addEventListener('message', event => {
  if (event.source !== frame.contentWindow) return;
  const data = event.data;
  if (!data || typeof data !== 'object') return;
  if (data.type === 'preview-ready') { initializeFrame(); return; }
  if (data.type === 'preview-theme' && ['dark','light'].includes(data.theme)) { previewTheme = data.theme; return; }
  if (data.type !== 'preview-route' || typeof data.path !== 'string') return;
  const path = data.path.startsWith('#') ? currentRoute + data.path : data.path;
  if (!Object.hasOwn(pages, path.split('#')[0])) return;
  const hash = '#' + encodeURIComponent(path);
  if (location.hash === hash) show(path);
  else location.hash = hash;
});
window.addEventListener('hashchange', () => show(routeFromHash()));
show(routeFromHash());
