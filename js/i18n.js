/** Geografia i18n: tg/ru/en — data-pf-i18n immune to app.js wipe */
(() => {
  const DICT = {
    tg: {
      navHome: 'Хона', navCountries: 'Кишварҳо', navCourses: 'Курсҳо', navQuizzes: 'Викторинаҳо',
      navOlympiads: 'Олимпиадаҳо', navLeaderboard: 'Рейтинг', navProfile: 'Профил', navSettings: 'Танзимот',
      language: 'Забон', theme: 'Тема', notif: 'Огоҳӣ',
      platformActivity: 'Фаъолияти платформа', liveDashboard: 'Дашборди зинда',
      countries: 'Кишварҳо', quizzes: 'Викторинаҳо', students: 'Хонандагон', olympiads: 'Олимпиадаҳо',
      featuredQuizzes: 'Викторинаҳои пешниҳодшуда', viewAll: 'Ҳама →', viewLeaderboard: 'Дидан →',
      leaderboard: 'Рейтинг · Беҳтаринҳо', leaderboardTitle: 'Рейтинг · Беҳтаринҳо',
      activityEmpty: 'Фаъолият ҳоло нест', olympEmpty: 'Фаъол нест', lbEmpty: 'Натиҷаҳо баъд аз супориш',
      resultsLog: 'results.log', live: 'live', olympiadActive: 'Олимпиада фаъол',
      quizAvailable: 'Викторина дастрас', now: 'ҳоло', noActivity: 'Фаъолият ҳоло нест',
      loading: 'Бор шуда истодааст...', error: 'Хато рух дод', notFound: 'Маълумот ёфт нашуд', success: 'Муваффақ шуд',
      save: 'Захира', cancel: 'Бекор', close: 'Пӯшидан', back: 'Бозгашт', backToSite: 'Бозгашт ба сайт',
      site: 'Сайт', logout: 'Баромадан', login: 'Воридшавӣ', loginGoogle: 'Воридшавӣ бо Google',
      quizTitle: 'Викторинаҳо',
      guestTitle: 'Корбари оддӣ?',
      guestText: 'Бо Google ворид шавед ва дар викторинаҳо иштирок кунед.',
      quizLead: 'Викторинаҳои ҷуғрофӣ — балл server-side, таймер, таърих дар профил.',
      history: 'Таърих',
      listEmpty: 'Ҳанӯз викторина нест. Админ метавонад аз API созад.',
      backToList: '← Рӯйхат',
      resultTitle: 'Натиҷа',
      historyHint: 'Барои нигоҳ доштани таърих бо Google ворид шавед.',
      authHint: 'Google — барои викторина ва таърих. Ё Student ID.',
      studentIdLabel: 'Student ID (хонанда)',
      saveStudentId: 'Сабти ID',

      all: 'Ҳама', search: 'Ҷустуҷӯ', searchPlaceholder: 'Ҷустуҷӯи кишвар...', empty: 'Холӣ',
      yes: 'Ҳа', no: 'Не', of: 'аз', questions: 'савол', question: 'Савол', passScore: 'Ҳад',
      minutes: 'дақ', seconds: 'сон', noLimit: 'Бе маҳдуд',
      heroTitle: 'Ҷуғрофияи Ҷаҳон',
      heroText: 'Сайти интерактивӣ бо ҳамаи кишварҳо, маълумоти муфассал ва харита.',
      regions: 'Минтақаҳо', population: 'Аҳолӣ', area: 'Масоҳат', capital: 'Пойтахт', countryCount: 'кишвар',
      coursesTitle: 'Курсҳо · Китобҳо ва маводҳо', coursesSub: 'Китобҳои ҷуғрофия, мақолаҳо ва маҷаллаҳо барои омӯзиш.',
      books: 'Китобҳо', articles: 'Мақолаҳо', magazines: 'Маҷаллаҳо', links: 'Пайвандҳо', emptyContent: 'Ҳоло мавод нест.',
      profile: 'Профил', rating: 'Рейтинг', contests: 'Мусобиқаҳо', solved: 'Ҳалшуда', participant: 'Иштирокчӣ',
      previous: '← Пештар', next: 'Баъдӣ →', submit: 'Супоридан', submitExam: 'Супоридан',
      questionXofY: 'Савол {n} / {total}', writeAnswerPlaceholder: 'Ҷавобро нависед...', noQuestion: 'Савол нест',
      startExam: 'Оғоз кардан', statusParticipated: 'Шумо иштирок кардаед', questionsCount: 'Саволҳо',
      submitConfirm: 'Оё мехоҳед супоред?', errGeneric: 'Хато рух дод', errLogin: 'ID нодуруст',
      studentLoginTitle: 'Воридшавии хонанда', studentLoginBtn: 'Ворид шудан', studentIdLabel: 'ID-и шумо',
      studentIdPlaceholder: 'Рақами донишҷӯ', studentLoginHint: 'Танҳо бо ID-е, ки админ додааст',
      activeOlympiads: 'Олимпиадаҳои фаъол', quizzesSection: 'Викторинаҳо',
      noActiveOlympiad: 'Ҳоло олимпиадаи фаъол нест.', noQuizzesStudent: 'Ҳоло викторина нест.',
      selectAnswer: 'Ҷавобро интихоб кунед', correct: 'Дуруст', waiting: 'Интизор',
      result: 'Натиҷа',
      lbParticipants: 'иштирокчӣ', lbAutoRefresh: 'навсозӣ автоматӣ', lbClosed: 'Рейтинг пӯшида аст.',
      lbColRank: 'Ҷой', lbColName: 'Иштирокчӣ', lbColRating: 'Рейтинг', lbColSolved: 'Ҳал', lbColContests: 'Мусобиқа',
      lbBackHome: '← Хона', lbSubtitle: 'Рейтинги ҳамаи иштирокчиён',
      create: 'Сохтан', edit: 'Таҳрир', delete: 'Нест кардан', export: 'Содирот', refresh: 'Навсозӣ',
    },
    ru: {
      navHome: 'Главная', navCountries: 'Страны', navCourses: 'Курсы', navQuizzes: 'Викторины',
      navOlympiads: 'Олимпиады', navLeaderboard: 'Рейтинг', navProfile: 'Профиль', navSettings: 'Настройки',
      language: 'Язык', theme: 'Тема', notif: 'Уведомления',
      platformActivity: 'Активность платформы', liveDashboard: 'Живая панель',
      countries: 'Страны', quizzes: 'Викторины', students: 'Ученики', olympiads: 'Олимпиады',
      featuredQuizzes: 'Рекомендуемые викторины', viewAll: 'Все →', viewLeaderboard: 'Смотреть →',
      leaderboard: 'Рейтинг · Топ', leaderboardTitle: 'Рейтинг · Лучшие',
      activityEmpty: 'Пока нет активности', olympEmpty: 'Нет активных', lbEmpty: 'Результаты появятся после сдачи',
      resultsLog: 'results.log', live: 'live', olympiadActive: 'Олимпиада активна',
      quizAvailable: 'Викторина доступна', now: 'сейчас', noActivity: 'Пока нет активности',
      loading: 'Загрузка...', error: 'Произошла ошибка', notFound: 'Данные не найдены', success: 'Успешно',
      save: 'Сохранить', cancel: 'Отмена', close: 'Закрыть', back: 'Назад', backToSite: 'Вернуться на сайт',
      site: 'Сайт', logout: 'Выйти', login: 'Вход', loginGoogle: 'Войти через Google',
      quizTitle: 'Викторины',
      guestTitle: 'Гость?',
      guestText: 'Войдите через Google и участвуйте в викторинах.',
      quizLead: 'Географические викторины — оценка на сервере, таймер, история в профиле.',
      history: 'История',
      listEmpty: 'Пока нет викторин. Админ может создать через API.',
      backToList: '← Список',
      resultTitle: 'Результат',
      historyHint: 'Чтобы сохранить историю, войдите через Google.',
      authHint: 'Google — для викторин и истории. Или Student ID.',
      studentIdLabel: 'Student ID (ученик)',
      saveStudentId: 'Сохранить ID',

      all: 'Все', search: 'Поиск', searchPlaceholder: 'Поиск страны...', empty: 'Пусто',
      yes: 'Да', no: 'Нет', of: 'из', questions: 'вопросов', question: 'Вопрос', passScore: 'Порог',
      minutes: 'мин', seconds: 'сек', noLimit: 'Без ограничения',
      heroTitle: 'География мира',
      heroText: 'Интерактивный сайт со всеми странами, подробными данными и картой.',
      regions: 'Регионы', population: 'Население', area: 'Площадь', capital: 'Столица', countryCount: 'стран',
      coursesTitle: 'Курсы · Книги и материалы', coursesSub: 'Учебники географии, статьи и журналы для обучения.',
      books: 'Книги', articles: 'Статьи', magazines: 'Журналы', links: 'Ссылки', emptyContent: 'Пока нет материалов.',
      profile: 'Профиль', rating: 'Рейтинг', contests: 'Соревнования', solved: 'Решено', participant: 'Участник',
      previous: '← Назад', next: 'Далее →', submit: 'Сдать', submitExam: 'Сдать работу',
      questionXofY: 'Вопрос {n} / {total}', writeAnswerPlaceholder: 'Напишите ответ...', noQuestion: 'Нет вопроса',
      startExam: 'Начать', statusParticipated: 'Вы уже участвовали', questionsCount: 'Вопросов',
      submitConfirm: 'Сдать работу?', errGeneric: 'Произошла ошибка', errLogin: 'Неверный ID',
      studentLoginTitle: 'Вход ученика', studentLoginBtn: 'Войти', studentIdLabel: 'Ваш ID',
      studentIdPlaceholder: 'Номер ученика', studentLoginHint: 'Только по ID администратора',
      activeOlympiads: 'Активные олимпиады', quizzesSection: 'Викторины',
      noActiveOlympiad: 'Сейчас нет активных олимпиад.', noQuizzesStudent: 'Сейчас нет викторин.',
      selectAnswer: 'Выберите ответ', correct: 'Верно', waiting: 'Ожидание', result: 'Результат',
      lbParticipants: 'участников', lbAutoRefresh: 'автообновление', lbClosed: 'Рейтинг закрыт.',
      lbColRank: 'Место', lbColName: 'Участник', lbColRating: 'Рейтинг', lbColSolved: 'Решено', lbColContests: 'Турниры',
      lbBackHome: '← Главная', lbSubtitle: 'Рейтинг всех участников',
      create: 'Создать', edit: 'Изменить', delete: 'Удалить', export: 'Экспорт', refresh: 'Обновить',
    },
    en: {
      navHome: 'Home', navCountries: 'Countries', navCourses: 'Courses', navQuizzes: 'Quizzes',
      navOlympiads: 'Olympiads', navLeaderboard: 'Leaderboard', navProfile: 'Profile', navSettings: 'Settings',
      language: 'Language', theme: 'Theme', notif: 'Notifications',
      platformActivity: 'Platform activity', liveDashboard: 'Live Dashboard',
      countries: 'Countries', quizzes: 'Quizzes', students: 'Students', olympiads: 'Olympiads',
      featuredQuizzes: 'Featured quizzes', viewAll: 'View all →', viewLeaderboard: 'View →',
      leaderboard: 'Leaderboard · Top Rated', leaderboardTitle: 'Leaderboard · Top',
      activityEmpty: 'No activity yet', olympEmpty: 'None active', lbEmpty: 'Results after submissions',
      resultsLog: 'results.log', live: 'live', olympiadActive: 'Olympiad active',
      quizAvailable: 'Quiz available', now: 'now', noActivity: 'No activity yet',
      loading: 'Loading...', error: 'An error occurred', notFound: 'Data not found', success: 'Success',
      save: 'Save', cancel: 'Cancel', close: 'Close', back: 'Back', backToSite: 'Back to site',
      site: 'Site', logout: 'Log out', login: 'Sign in', loginGoogle: 'Sign in with Google',
      quizTitle: 'Quizzes',
      guestTitle: 'Guest?',
      guestText: 'Sign in with Google to take quizzes.',
      quizLead: 'Geography quizzes — server-side scoring, timer, history in profile.',
      history: 'History',
      listEmpty: 'No quizzes yet. Admin can create via API.',
      backToList: '← List',
      resultTitle: 'Result',
      historyHint: 'Sign in with Google to keep history.',
      authHint: 'Google — for quizzes and history. Or Student ID.',
      studentIdLabel: 'Student ID',
      saveStudentId: 'Save ID',

      all: 'All', search: 'Search', searchPlaceholder: 'Search country...', empty: 'Empty',
      yes: 'Yes', no: 'No', of: 'of', questions: 'questions', question: 'Question', passScore: 'Pass',
      minutes: 'min', seconds: 'sec', noLimit: 'No limit',
      heroTitle: 'World Geography',
      heroText: 'Interactive site with all countries, detailed data and map.',
      regions: 'Regions', population: 'Population', area: 'Area', capital: 'Capital', countryCount: 'countries',
      coursesTitle: 'Courses · Books & materials', coursesSub: 'Geography textbooks, articles and magazines for learning.',
      books: 'Books', articles: 'Articles', magazines: 'Magazines', links: 'Links', emptyContent: 'No materials yet.',
      profile: 'Profile', rating: 'Rating', contests: 'Contests', solved: 'Solved', participant: 'Participant',
      previous: '← Previous', next: 'Next →', submit: 'Submit', submitExam: 'Submit',
      questionXofY: 'Question {n} / {total}', writeAnswerPlaceholder: 'Write your answer...', noQuestion: 'No question',
      startExam: 'Start', statusParticipated: 'You have already participated', questionsCount: 'Questions',
      submitConfirm: 'Submit your answers?', errGeneric: 'An error occurred', errLogin: 'Invalid ID',
      studentLoginTitle: 'Student login', studentLoginBtn: 'Sign in', studentIdLabel: 'Your ID',
      studentIdPlaceholder: 'Student number', studentLoginHint: 'Only with an admin-issued ID',
      activeOlympiads: 'Active olympiads', quizzesSection: 'Quizzes',
      noActiveOlympiad: 'No active olympiads right now.', noQuizzesStudent: 'No quizzes right now.',
      selectAnswer: 'Select an answer', correct: 'Correct', waiting: 'Waiting', result: 'Result',
      lbParticipants: 'participants', lbAutoRefresh: 'auto-refresh', lbClosed: 'Leaderboard is closed.',
      lbColRank: 'Rank', lbColName: 'Participant', lbColRating: 'Rating', lbColSolved: 'Solved', lbColContests: 'Contests',
      lbBackHome: '← Home', lbSubtitle: 'Ratings of all participants',
      create: 'Create', edit: 'Edit', delete: 'Delete', export: 'Export', refresh: 'Refresh',
    },
  };

  function normalize(code) {
    if (!code) return 'tg';
    code = String(code).toLowerCase();
    if (code === 'tj' || code === 'tjik' || code === 'tajik') return 'tg';
    if (code === 'ru' || code === 'en' || code === 'tg') return code;
    return 'tg';
  }

  function lang() {
    const raw =
      localStorage.getItem('geografia_lang') ||
      localStorage.getItem('geo_lang') ||
      localStorage.getItem('siteLanguage') ||
      'tg';
    return normalize(raw);
  }

  function setLang(code) {
    code = normalize(code);
    localStorage.setItem('geografia_lang', code);
    localStorage.setItem('geo_lang', code);
    localStorage.setItem('siteLanguage', code);
    document.documentElement.lang = code === 'tg' ? 'tg' : code;
    apply();
    try {
      if (typeof window.applyLanguage === 'function') window.applyLanguage(code);
    } catch (e) {}
    apply();
    document.querySelectorAll('#pfLang, #languageSelect, [data-lang-select]').forEach((sel) => {
      if (!sel) return;
      if (sel.querySelector('option[value="tg"]')) sel.value = code;
      else if (sel.querySelector('option[value="tj"]')) sel.value = code === 'tg' ? 'tj' : code;
      else sel.value = code;
    });
    window.dispatchEvent(new CustomEvent('geo:lang', { detail: code }));
  }

  function t(key, params) {
    if (!key) return '';
    const d = DICT[lang()] || DICT.tg;
    let s = d[key];
    if (s == null) s = (DICT.en && DICT.en[key]) || (DICT.tg && DICT.tg[key]) || key;
    if (params && typeof s === 'string') {
      Object.keys(params).forEach((k) => {
        s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), String(params[k]));
      });
    }
    return s;
  }

  function apply() {
    document.querySelectorAll('[data-i18n], [data-pf-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n') || el.getAttribute('data-pf-i18n');
      const val = t(key);
      // If key missing from dict, t() returns the key — keep existing HTML fallback text
      if (val === key && el.textContent && el.textContent.trim() && el.textContent.trim() !== key) {
        return;
      }
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        if (!el.getAttribute('data-i18n-value')) el.placeholder = val;
        else el.value = val;
      } else el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-placeholder], [data-pf-placeholder]').forEach((el) => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder') || el.getAttribute('data-pf-placeholder'));
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
  }

  function bind() {
    document.querySelectorAll('#pfLang, #languageSelect, [data-lang-select]').forEach((sel) => {
      if (!sel || sel._i18nBound) return;
      sel._i18nBound = true;
      const cur = lang();
      if (sel.querySelector('option[value="tg"]')) sel.value = cur;
      else if (sel.querySelector('option[value="tj"]')) sel.value = cur === 'tg' ? 'tj' : cur;
      else sel.value = cur;
      sel.addEventListener('change', () => setLang(sel.value));
    });
    apply();
  }

  function onLang(fn) {
    if (typeof fn !== 'function') return;
    window.addEventListener('geo:lang', (e) => fn(e.detail));
  }

  function syncAppLang() {
    const code = lang();
    localStorage.setItem('siteLanguage', code);
    try {
      if (typeof window.applyLanguage === 'function') window.applyLanguage(code);
    } catch (e) {}
    apply();
  }

  function bootI18n() {
    bind();
    syncAppLang();
    [200, 600, 1200, 2500, 5000].forEach(function (ms) { setTimeout(syncAppLang, ms); });
  }

  window.GeoI18n = { t, setLang, lang, apply, onLang, DICT, normalize };
  window.t = t;

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootI18n);
  else bootI18n();
})();
