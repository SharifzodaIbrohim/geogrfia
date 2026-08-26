/** admin-results-review loader — joins _rr_p0 + _rr_p1 */
(async function () {
  try {
    const base = (document.currentScript && document.currentScript.src) || '';
    const dir = base.replace(/[^/]+$/, '');
    const [a, b] = await Promise.all([
      fetch(dir + '_rr_p0.txt', { credentials: 'same-origin' }).then(r => r.text()),
      fetch(dir + '_rr_p1.txt', { credentials: 'same-origin' }).then(r => r.text()),
    ]);
    const code = a + b;
    const s = document.createElement('script');
    s.textContent = code;
    document.head.appendChild(s);
  } catch (e) {
    console.error('admin-results-review load failed', e);
  }
})();
