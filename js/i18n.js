(() => {
  const DICT = {
    tg: {
      navHome: 'Хона',
      navCountries: 'Кишварҳо',
      navCourses: 'Courses',
      navQuizzes: 'Викторинаҳо',
      navOlympiads: 'Олимпиадаҳо',
      navProfile: 'Профил',
      navLeaderboard: 'Рейтинг',
      heroTitle: 'Ҷуғрофияи Ҷаҳон',
      heroText: 'Сайти интерактивӣ бо ҳамаи кишварҳо, маълумоти муфассал ва харита.',
      coursesTitle: 'Courses · Китобҳо ва маводҳо',
      coursesSub: 'Китобҳои ҷуғрофия, мақолаҳо ва маҷаллаҳо барои омӯзиш.',
      all: 'Ҳама', books: 'Китобҳо', articles: 'Мақолаҳо', magazines: 'Маҷаллаҳо', links: 'Пайвандҳо',
      emptyContent: 'Ҳоло мавод нест.',
      liveDashboard: 'Live Dashboard',
      countries: 'Кишварҳо', quizzes: 'Викторинаҳо', students: 'Хонандагон', olympiads: 'Олимпиадаҳо',
      login: 'Воридшавӣ', profile: 'Профил', theme: 'Тема', notif: 'Огоҳӣ',
    },
    ru: {
      navHome: 'Главная',
      navCountries: 'Страны',
      navCourses: 'Курсы',
      navQuizzes: 'Викторины',
      navOlympiads: 'Олимпиады',
      navProfile: 'Профиль',
      navLeaderboard: 'Рейтинг',
      heroTitle: 'География мира',
      heroText: 'Интерактивный сайт со всеми странами, подробными данными и картой.',
      coursesTitle: 'Курсы · Книги и материалы',
      coursesSub: 'Учебники географии, статьи и журналы для обучения.',
      all: 'Все', books: 'Книги', articles: 'Статьи', magazines: 'Журналы', links: 'Ссылки',
      emptyContent: 'Пока нет материалов.',
      liveDashboard: 'Live Dashboard',
      countries: 'Страны', quizzes: 'Викторины', students: 'Ученики', olympiads: 'Олимпиады',
      login: 'Вход', profile: 'Профиль', theme: 'Тема', notif: 'Уведомления',
    },
    en: {
      navHome: 'Home',
      navCountries: 'Countries',
      navCourses: 'Courses',
      navQuizzes: 'Quizzes',
      navOlympiads: 'Olympiads',
      navProfile: 'Profile',
      navLeaderboard: 'Leaderboard',
      heroTitle: 'World Geography',
      heroText: 'Interactive site with all countries, detailed data and map.',
      coursesTitle: 'Courses · Books & materials',
      coursesSub: 'Geography textbooks, articles and magazines for learning.',
      all: 'All', books: 'Books', articles: 'Articles', magazines: 'Magazines', links: 'Links',
      emptyContent: 'No materials yet.',
      liveDashboard: 'Live Dashboard',
      countries: 'Countries', quizzes: 'Quizzes', students: 'Students', olympiads: 'Olympiads',
      login: 'Sign in', profile: 'Profile', theme: 'Theme', notif: 'Notifications',
    },
  };

  function lang() {
    return localStorage.getItem('geo_lang') || 'tg';
  }

  function setLang(code) {
    if (!DICT[code]) code = 'tg';
    localStorage.setItem('geo_lang', code);
    document.documentElement.lang = code === 'tg' ? 'tg' : code;
    apply();
    const sel = document.getElementById('pfLang');
    if (sel) sel.value = code;
    const legacy = document.getElementById('languageSelect');
    if (legacy) legacy.value = code;
    window.dispatchEvent(new CustomEvent('geo:lang', { detail: code }));
  }

  function t(key) {
    const d = DICT[lang()] || DICT.tg;
    return d[key] || DICT.tg[key] || key;
  }

  function apply() {
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const val = t(key);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.placeholder = val;
      } else {
        el.textContent = val;
      }
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
  }

  function bind() {
    const sel = document.getElementById('pfLang');
    if (sel) {
      sel.value = lang();
      sel.addEventListener('change', () => setLang(sel.value));
    }
    const legacy = document.getElementById('languageSelect');
    if (legacy) {
      legacy.value = lang();
      legacy.addEventListener('change', () => setLang(legacy.value));
    }
    apply();
  }

  window.GeoI18n = { t, setLang, lang, apply, DICT };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
