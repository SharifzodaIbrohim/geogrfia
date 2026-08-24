/**
 * Geografia full i18n — see artifacts; bridge siteLanguage + applyLanguage
 */
(() => {
  const DICT = {
    tg: {
      navHome: 'Хона', navCountries: 'Кишварҳо', navCourses: 'Курсҳо', navQuizzes: 'Викторинаҳо',
      navOlympiads: 'Олимпиадаҳо', navLeaderboard: 'Рейтинг', navProfile: 'Профил',
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
      all: 'Ҳама', search: 'Ҷустуҷӯ', searchPlaceholder: 'Ҷустуҷӯи кишвар...', empty: 'Холӣ',
      yes: 'Ҳа', no: 'Не', of: 'аз', questions: 'савол', question: 'Савол', passScore: 'Ҳад',
      minutes: 'дақ', seconds: 'сон', noLimit: 'Бе маҳдуд',
      heroTitle: 'Ҷуғрофияи Ҷаҳон',
      heroText: 'Сайти интерактивӣ бо ҳамаи кишварҳо, маълумоти муфассал ва харита.',
      regions: 'Минтақаҳо', population: 'Аҳолӣ', area: 'Масоҳат', capital: 'Пойтахт', countryCount: 'кишвар',
      coursesTitle: 'Курсҳо · Китобҳо ва маводҳо', coursesSub: 'Китобҳои ҷуғрофия, мақолаҳо ва маҷаллаҳо барои омӯзиш.',
      books: 'Китобҳо', articles: 'Мақолаҳо', magazines: 'Маҷаллаҳо', links: 'Пайвандҳо', emptyContent: 'Ҳоло мавод нест.',
      profile: 'Профил', rating: 'Рейтинг', contests: 'Мусобиқаҳо', solved: 'Ҳалшуда', participant: 'Иштирокчӣ',
      guestTitle: 'Корбари оддӣ?', guestText: 'Бо Google ворид шавед ва дар викторинаҳо иштирок кунед.',
      gender: 'Ҷинс', male: 'Мард', female: 'Зан', school: 'Мактаб', region: 'Минтақа', className: 'Синф',
      fullName: 'Номи пурра', onboardingSave: 'Захира кардан',
      profileGate: 'Барои дидани профил ва иштирок дар викторинаҳо бо Google ворид шавед.',
      quizTitle: 'Викторинаҳо', quizLead: 'Викторинаҳои ҷуғрофӣ — балл server-side, таймер, таърих дар профил.',
      history: 'Таърих', startQuiz: 'Оғоз кардан', continueQuiz: 'Идома додан', noQuizzes: 'Ҳанӯз викторина нест.',
      studentLoginTitle: 'Воридшавии хонанда', studentLoginHint: 'Танҳо бо ID-е, ки админ додааст',
      studentIdLabel: 'ID-и шумо', studentIdPlaceholder: 'Рақами донишҷӯ', studentLoginBtn: 'Ворид шудан',
      activeOlympiads: 'Олимпиадаҳои фаъол', quizzesSection: 'Викторинаҳо',
      noActiveOlympiad: 'Ҳоло олимпиадаи фаъол нест.', noQuizzesStudent: 'Ҳоло викторина нест.',
      statusActive: 'Фаъол', statusUpcoming: 'Ба наздикӣ', statusFinished: 'Анҷомёфта',
      statusParticipated: 'Шумо иштирок кардаед', statusInProgress: 'Дар ҷараён', statusLocked: 'Қулфшуда',
      start: 'Оғоз', startExam: 'Оғоз кардан', continueExam: 'Идома додан', questionsCount: 'Саволҳо',
      previous: '← Пештар', next: 'Баъдӣ →', submit: 'Супоридан', submitExam: 'Супоридан',
      timeLeft: 'Вақти боқимонда', questionOf: 'Савол {n} аз {total}', questionXofY: 'Савол {n} / {total}',
      selectAnswer: 'Ҷавобро интихоб кунед', writeAnswer: 'Ҷавобро нависед',
      writeAnswerPlaceholder: 'Ҷавобро нависед...', matchingHint: 'Ҷуфтҳоро мувофиқ кунед',
      shortAnswer: 'Ҷавоби кӯтоҳ', textAnswer: 'Ҷавоби матнӣ', noQuestion: 'Савол нест',
      result: 'Натиҷа', score: 'Хол', percent: 'Фоиз', correct: 'Дуруст', incorrect: 'Нодуруст',
      passed: 'Шумо гузаштед', failed: 'Шумо нагузаштед', waiting: 'Интизор', backToList: 'Бозгашт ба рӯйхат',
      attemptUsed: 'Шумо аллакай ин олимпиадаро супоридаед', secondAttemptDenied: 'Кӯшиши дуюм иҷозат дода намешавад',
      timeUp: 'Вақт тамом шуд', submitConfirm: 'Оё мехоҳед супоред?', autosaved: 'Захира шуд',
      oneAttempt: 'Як кӯшиш', resume: 'Идома',
      errGeneric: 'Хато рух дод', errLogin: 'ID нодуруст ё вуруд нашуд', errNetwork: 'Пайвастшавӣ хато',
      errForbidden: 'Иҷозат нест', errExpired: 'Вақт тамом шуд', errAlreadySubmitted: 'Аллакай супорида шудааст',
      errNotAssigned: 'Шумо ба ин олимпиада таъин нашудаед', errLocked: 'Олимпиада қулфшуда аст',
      adminLogin: 'Воридшавии админ', adminPanel: 'Панели админ',
      tabStudents: 'Хонандагон', tabOlympiads: 'Олимпиадаҳо', tabResults: 'Натиҷаҳо', tabLeaderboard: 'Рейтинг',
      tabGmail: 'Gmail корбарон', tabContent: 'Контент', tabAdmins: 'Админҳо',
      create: 'Сохтан', edit: 'Таҳрир', delete: 'Нест кардан', export: 'Содирот', refresh: 'Навсозӣ',
    },
    ru: {
      navHome: 'Главная', navCountries: 'Страны', navCourses: 'Курсы', navQuizzes: 'Викторины',
      navOlympiads: 'Олимпиады', navLeaderboard: 'Рейтинг', navProfile: 'Профиль',
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
      all: 'Все', search: 'Поиск', searchPlaceholder: 'Поиск страны...', empty: 'Пусто',
      yes: 'Да', no: 'Нет', of: 'из', questions: 'вопросов', question: 'Вопрос', passScore: 'Порог',
      minutes: 'мин', seconds: 'сек', noLimit: 'Без ограничения',
      heroTitle: 'География мира',
      heroText: 'Интерактивный сайт со всеми странами, подробными данными и картой.',
      regions: 'Регионы', population: 'Население', area: 'Площадь', capital: 'Столица', countryCount: 'стран',
      coursesTitle: 'Курсы · Книги и материалы', coursesSub: 'Учебники географии, статьи и журналы для обучения.',
      books: 'Книги', articles: 'Статьи', magazines: 'Журналы', links: 'Ссылки', emptyContent: 'Пока нет материалов.',
      profile: 'Профиль', rating: 'Рейтинг', contests: 'Соревнования', solved: 'Решено', participant: 'Участник',
      guestTitle: 'Обычный пользователь?', guestText: 'Войдите через Google и участвуйте в викторинах.',
      gender: 'Пол', male: 'Мужской', female: 'Женский', school: 'Школа', region: 'Регион', className: 'Класс',
      fullName: 'ФИО', onboardingSave: 'Сохранить',
      profileGate: 'Чтобы увидеть профиль и участвовать в викторинах, войдите через Google.',
      quizTitle: 'Викторины', quizLead: 'Географические викторины — серверный балл, таймер, история в профиле.',
      history: 'История', startQuiz: 'Начать', continueQuiz: 'Продолжить', noQuizzes: 'Пока нет викторин.',
      studentLoginTitle: 'Вход ученика', studentLoginHint: 'Только по ID, выданному администратором',
      studentIdLabel: 'Ваш ID', studentIdPlaceholder: 'Номер ученика', studentLoginBtn: 'Войти',
      activeOlympiads: 'Активные олимпиады', quizzesSection: 'Викторины',
      noActiveOlympiad: 'Сейчас нет активных олимпиад.', noQuizzesStudent: 'Сейчас нет викторин.',
      statusActive: 'Активна', statusUpcoming: 'Скоро', statusFinished: 'Завершена',
      statusParticipated: 'Вы уже участвовали', statusInProgress: 'В процессе', statusLocked: 'Заблокировано',
      start: 'Старт', startExam: 'Начать', continueExam: 'Продолжить', questionsCount: 'Вопросов',
      previous: '← Назад', next: 'Далее →', submit: 'Сдать', submitExam: 'Сдать работу',
      timeLeft: 'Осталось времени', questionOf: 'Вопрос {n} из {total}', questionXofY: 'Вопрос {n} / {total}',
      selectAnswer: 'Выберите ответ', writeAnswer: 'Напишите ответ',
      writeAnswerPlaceholder: 'Напишите ответ...', matchingHint: 'Сопоставьте пары',
      shortAnswer: 'Краткий ответ', textAnswer: 'Текстовый ответ', noQuestion: 'Нет вопроса',
      result: 'Результат', score: 'Балл', percent: 'Процент', correct: 'Верно', incorrect: 'Неверно',
      passed: 'Вы прошли', failed: 'Вы не прошли', waiting: 'Ожидание', backToList: 'К списку',
      attemptUsed: 'Вы уже сдали эту олимпиаду', secondAttemptDenied: 'Вторая попытка не разрешена',
      timeUp: 'Время вышло', submitConfirm: 'Сдать работу?', autosaved: 'Сохранено',
      oneAttempt: 'Одна попытка', resume: 'Продолжить',
      errGeneric: 'Произошла ошибка', errLogin: 'Неверный ID или вход не выполнен', errNetwork: 'Ошибка сети',
      errForbidden: 'Нет доступа', errExpired: 'Время вышло', errAlreadySubmitted: 'Уже сдано',
      errNotAssigned: 'Вы не назначены на эту олимпиаду', errLocked: 'Олимпиада заблокирована',
      adminLogin: 'Вход администратора', adminPanel: 'Панель администратора',
      tabStudents: 'Ученики', tabOlympiads: 'Олимпиады', tabResults: 'Результаты', tabLeaderboard: 'Рейтинг',
      tabGmail: 'Gmail пользователи', tabContent: 'Контент', tabAdmins: 'Админы',
      create: 'Создать', edit: 'Изменить', delete: 'Удалить', export: 'Экспорт', refresh: 'Обновить',
    },
    en: {
      navHome: 'Home', navCountries: 'Countries', navCourses: 'Courses', navQuizzes: 'Quizzes',
      navOlympiads: 'Olympiads', navLeaderboard: 'Leaderboard', navProfile: 'Profile',
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
      all: 'All', search: 'Search', searchPlaceholder: 'Search country...', empty: 'Empty',
      yes: 'Yes', no: 'No', of: 'of', questions: 'questions', question: 'Question', passScore: 'Pass',
      minutes: 'min', seconds: 'sec', noLimit: 'No limit',
      heroTitle: 'World Geography',
      heroText: 'Interactive site with all countries, detailed data and map.',
      regions: 'Regions', population: 'Population', area: 'Area', capital: 'Capital', countryCount: 'countries',
      coursesTitle: 'Courses · Books & materials', coursesSub: 'Geography textbooks, articles and magazines for learning.',
      books: 'Books', articles: 'Articles', magazines: 'Magazines', links: 'Links', emptyContent: 'No materials yet.',
      profile: 'Profile', rating: 'Rating', contests: 'Contests', solved: 'Solved', participant: 'Participant',
      guestTitle: 'Regular user?', guestText: 'Sign in with Google to take quizzes.',
      gender: 'Gender', male: 'Male', female: 'Female', school: 'School', region: 'Region', className: 'Class',
      fullName: 'Full name', onboardingSave: 'Save',
      profileGate: 'Sign in with Google to view your profile and take quizzes.',
      quizTitle: 'Quizzes', quizLead: 'Geography quizzes — server scoring, timer, history in profile.',
      history: 'History', startQuiz: 'Start', continueQuiz: 'Continue', noQuizzes: 'No quizzes yet.',
      studentLoginTitle: 'Student login', studentLoginHint: 'Only with an ID issued by the admin',
      studentIdLabel: 'Your ID', studentIdPlaceholder: 'Student number', studentLoginBtn: 'Sign in',
      activeOlympiads: 'Active olympiads', quizzesSection: 'Quizzes',
      noActiveOlympiad: 'No active olympiads right now.', noQuizzesStudent: 'No quizzes right now.',
      statusActive: 'Active', statusUpcoming: 'Upcoming', statusFinished: 'Finished',
      statusParticipated: 'You have already participated', statusInProgress: 'In progress', statusLocked: 'Locked',
      start: 'Start', startExam: 'Start', continueExam: 'Continue', questionsCount: 'Questions',
      previous: '← Previous', next: 'Next →', submit: 'Submit', submitExam: 'Submit',
      timeLeft: 'Time left', questionOf: 'Question {n} of {total}', questionXofY: 'Question {n} / {total}',
      selectAnswer: 'Select an answer', writeAnswer: 'Write your answer',
      writeAnswerPlaceholder: 'Write your answer...', matchingHint: 'Match the pairs',
      shortAnswer: 'Short answer', textAnswer: 'Text answer', noQuestion: 'No question',
      result: 'Result', score: 'Score', percent: 'Percent', correct: 'Correct', incorrect: 'Incorrect',
      passed: 'You passed', failed: 'You did not pass', waiting: 'Waiting', backToList: 'Back to list',
      attemptUsed: 'You have already submitted this olympiad', secondAttemptDenied: 'A second attempt is not allowed',
      timeUp: 'Time is up', submitConfirm: 'Submit your answers?', autosaved: 'Saved',
      oneAttempt: 'One attempt', resume: 'Resume',
      errGeneric: 'An error occurred', errLogin: 'Invalid ID or login failed', errNetwork: 'Network error',
      errForbidden: 'Access denied', errExpired: 'Time expired', errAlreadySubmitted: 'Already submitted',
      errNotAssigned: 'You are not assigned to this olympiad', errLocked: 'Olympiad is locked',
      adminLogin: 'Admin login', adminPanel: 'Admin panel',
      tabStudents: 'Students', tabOlympiads: 'Olympiads', tabResults: 'Results', tabLeaderboard: 'Leaderboard',
      tabGmail: 'Gmail users', tabContent: 'Content', tabAdmins: 'Admins',
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
    var ls = document.getElementById('languageSelect');
    if (ls && ls.value !== code) { try { ls.value = code; } catch (e) {} }
    document.querySelectorAll('#pfLang, #languageSelect, [data-lang-select]').forEach((sel) => {
      if (!sel) return;
      if (sel.querySelector('option[value="tg"]')) sel.value = code;
      else if (sel.querySelector('option[value="tj"]')) sel.value = code === 'tg' ? 'tj' : code;
      else sel.value = code;
    });
    window.dispatchEvent(new CustomEvent('geo:lang', { detail: code }));
    try { window.dispatchEvent(new CustomEvent('geografia:lang', { detail: code })); } catch (e) {}
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
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const val = t(key);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        if (!el.getAttribute('data-i18n-value')) el.placeholder = val;
        else el.value = val;
      } else el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
    document.querySelectorAll('[data-i18n-html]').forEach((el) => {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
    const mapPairs = [['.pf-dash-title', 'liveDashboard'], ['.pf-kicker', 'platformActivity']];
    mapPairs.forEach(([sel, key]) => {
      document.querySelectorAll(sel).forEach((el) => {
        if (!el.getAttribute('data-i18n')) el.textContent = t(key);
      });
    });
    const prev = document.getElementById('examPrevBtn');
    if (prev) prev.textContent = t('previous');
    const next = document.getElementById('examNextBtn');
    if (next) next.textContent = t('next');
    const sub = document.getElementById('submitExamBtn');
    if (sub) sub.textContent = t('submitExam');
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
    window.addEventListener('geografia:lang', (e) => fn(e.detail));
  }

  function syncAppLang() {
    const code = lang();
    localStorage.setItem('siteLanguage', code);
    try {
      if (typeof window.applyLanguage === 'function') window.applyLanguage(code);
    } catch (e) {}
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
