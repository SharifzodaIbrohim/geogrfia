/*! Fix: update #countryCount when countries list renders (was stuck at "0 кишвар") */
(function () {
  function label(n, lang) {
    n = Number(n) || 0;
    if (lang === 'en') return n === 1 ? 'country' : 'countries';
    if (lang === 'ru') return n === 1 ? 'страна' : 'стран';
    return 'кишвар';
  }
  function updateCount(n) {
    var el = document.getElementById('countryCount');
    if (!el) return;
    var lang = (localStorage.getItem('siteLanguage') || localStorage.getItem('geo_lang') || document.documentElement.lang || 'tg').slice(0, 2);
    el.textContent = n + ' ' + label(n, lang);
  }
  function countCards() {
    var cards = document.querySelectorAll('#results .country-card');
    updateCount(cards.length);
  }
  function startObs() {
    var grid = document.getElementById('results');
    if (!grid) return;
    countCards();
    var obs = new MutationObserver(function () { countCards(); });
    obs.observe(grid, { childList: true, subtree: false });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startObs);
  else startObs();
  // late safety
  setTimeout(countCards, 1500);
  setTimeout(countCards, 4000);
})();
