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
      platformActivity: 'Фаъолияти платформа',
      countries: 'Кишварҳо', quizzes: 'Викторинаҳо', students: 'Хонандагон', olympiads: 'Олимпиадаҳо',
      featuredQuizzes: 'Викторинаҳои пешниҳодшуда',
      viewAll: 'Ҳама →',
      leaderboard: 'Leaderboard · Top Rated',
      activityEmpty: 'Фаъолият ҳоло нест',
      olympEmpty: 'Фаъол нест',
      lbEmpty: 'Натиҷаҳо баъд аз супориш',
      login: 'Воридшавӣ',
      loginGoogle: 'Воридшавӣ бо Google',
      profile: 'Профил', theme: 'Тема', notif: 'Огоҳӣ',
      guestTitle: 'Корбари оддӣ?',
      guestText: 'Бо Google ворид шавед ва дар викторинаҳо иштирок кунед.',
      quizLead: 'Викторинаҳои ҷуғрофӣ — балл server-side, таймер, таърих дар профил.',
      quizTitle: 'Викторинаҳо',
      history: 'Таърих',
      searchPlaceholder: 'Ҷустуҷӯи кишвар...',
      regions: 'Минтақаҳо',
      passScore: 'Ҳад',
      questions: 'савол',
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
      platformActivity: 'Активность платформы',
      countries: 'Страны', quizzes: 'Викторины', students: 'Ученики', olympiads: 'Олимпиады',
      featuredQuizzes: 'Рекомендуемые викторины',
      viewAll: 'Все →',
      leaderboard: 'Рейтинг · Топ',
      activityEmpty: 'Пока нет активности',
      olympEmpty: 'Нет активных',
      lbEmpty: 'Результаты появятся после сдачи',
      login: 'Вход',
      loginGoogle: 'Войти через Google',
      profile: 'Профиль', theme: 'Тема', notif: 'Уведомления',
      guestTitle: 'Обычный пользователь?',
      guestText: 'Войдите через Google и участвуйте в викторинах.',
      quizLead: 'Географические викторины — серверный балл, таймер, история в профиле.',
      quizTitle: 'Викторины',
      history: 'История',
      searchPlaceholder: 'Поиск страны...',
      regions: 'Регионы',
      passScore: 'Порог',
      questions: 'вопросов',
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
      platformActivity: 'Platform activity',
      countries: 'Countries', quizzes: 'Quizzes', students: 'Students', olympiads: 'Olympiads',
      featuredQuizzes: 'Featured quizzes',
      viewAll: 'View all →',
      leaderboard: 'Leaderboard · Top Rated',
      activityEmpty: 'No activity yet',
      olympEmpty: 'None active',
      lbEmpty: 'Results after submissions',
      login: 'Sign in',
      loginGoogle: 'Sign in with Google',
      profile: 'Profile', theme: 'Theme', notif: 'Notifications',
      guestTitle: 'Regular user?',
      guestText: 'Sign in with Google to take quizzes.',
      quizLead: 'Geography quizzes — server scoring, timer, history in profile.',
      quizTitle: 'Quizzes',
      history: 'History',
      searchPlaceholder: 'Search country...',
      regions: 'Regions',
      passScore: 'Pass',
      questions: 'questions',
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
    document.querySelectorAll('#pfLang, #languageSelect').forEach((sel) => {
      if (sel) sel.value = code;
    });
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
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = val;
      else el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
    const mapPairs = [
      ['.pf-dash-title', 'liveDashboard'],
      ['.pf-kicker', 'platformActivity'],
    ];
    mapPairs.forEach(([sel, key]) => {
      document.querySelectorAll(sel).forEach((el) => {
        if (!el.getAttribute('data-i18n')) el.textContent = t(key);
      });
    });
  }

  function bind() {
    document.querySelectorAll('#pfLang, #languageSelect').forEach((sel) => {
      if (!sel || sel._i18nBound) return;
      sel._i18nBound = true;
      sel.value = lang();
      sel.addEventListener('change', () => setLang(sel.value));
    });
    apply();
  }

  window.GeoI18n = { t, setLang, lang, apply, DICT };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();
