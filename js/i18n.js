/** Geografia site i18n — tg / ru / en */
(function (global) {
  'use strict';

  const DICT = {
    tg: {
      home: 'Асосӣ', countries: 'Кишварҳо', quiz: 'Викторина', courses: 'Курсҳо',
      leaderboard: 'Рейтинг', profile: 'Профил', student: 'Хонанда', login: 'Ворид',
      logout: 'Баромадан', settings: 'Танзимот', language: 'Забон', theme: 'Мавзӯъ',
      dark: 'Торик', light: 'Равшан', search: 'Ҷустуҷӯ', loading: 'Боркунӣ…',
      error: 'Хато', save: 'Сабт', cancel: 'Бекор', delete: 'Нест', edit: 'Таҳрир',
      create: 'Сохтан', back: 'Бозгашт', next: 'Баъдӣ', previous: 'Пештар',
      submit: 'Супоридан', yes: 'Ҳа', no: 'Не', of: 'аз', questions: 'савол',
      question: 'Савол', questionLabel: 'Савол', passScore: 'Ҳад',
      minutes: 'дақиқа', noLimit: 'Бе маҳдудият', timeUp: 'Вақт тамом шуд.',
      yourScore: 'Холи шумо', submitted: 'Супорида шуд', leaveExam: 'Аз имтиҳон баромадан?',
      noQuestions: 'Саволҳо ёфт нашуданд.', startExam: 'Оғоз кардан',
      statusParticipated: 'Шумо иштирок кардаед', questionsCount: 'Саволҳо',
      questionXofY: 'Савол {n} / {total}', writeAnswerPlaceholder: 'Ҷавобро нависед...',
      noQuestion: 'Савол нест', activeOlympiads: 'Олимпиадаҳои фаъол',
      quizzesSection: 'Викторинаҳо', noActiveOlympiad: 'Ҳоло олимпиадаи фаъол нест.',
      noQuizzesStudent: 'Ҳоло викторина нест.', studentLoginTitle: 'Воридшавии хонанда',
      studentLoginHint: 'Танҳо бо ID-е, ки админ додааст', studentIdLabel: 'ID-и шумо',
      studentIdPlaceholder: 'Рақами донишҷӯ', studentLoginBtn: 'Ворид шудан',
      backToSite: 'Бозгашт ба сайт', site: 'Сайт', result: 'Натиҷа',
      submitExam: 'Супоридан',
    },
    ru: {
      home: 'Главная', countries: 'Страны', quiz: 'Викторина', courses: 'Курсы',
      leaderboard: 'Рейтинг', profile: 'Профиль', student: 'Ученик', login: 'Вход',
      logout: 'Выйти', settings: 'Настройки', language: 'Язык', theme: 'Тема',
      dark: 'Тёмная', light: 'Светлая', search: 'Поиск', loading: 'Загрузка…',
      error: 'Ошибка', save: 'Сохранить', cancel: 'Отмена', delete: 'Удалить',
      edit: 'Изменить', create: 'Создать', back: 'Назад', next: 'Далее',
      previous: 'Назад', submit: 'Отправить', yes: 'Да', no: 'Нет', of: 'из',
      questions: 'вопросов', question: 'Вопрос', questionLabel: 'Вопрос', passScore: 'Порог',
      minutes: 'мин', noLimit: 'Без лимита', timeUp: 'Время вышло.',
      yourScore: 'Ваш балл', submitted: 'Отправлено', leaveExam: 'Покинуть экзамен?',
      noQuestions: 'Вопросы не найдены.', startExam: 'Начать',
      statusParticipated: 'Вы уже участвовали', questionsCount: 'Вопросов',
      questionXofY: 'Вопрос {n} / {total}', writeAnswerPlaceholder: 'Напишите ответ...',
      noQuestion: 'Нет вопроса', activeOlympiads: 'Активные олимпиады',
      quizzesSection: 'Викторины', noActiveOlympiad: 'Нет активных олимпиад.',
      noQuizzesStudent: 'Нет викторин.', studentLoginTitle: 'Вход ученика',
      studentLoginHint: 'Только ID, выданный админом', studentIdLabel: 'Ваш ID',
      studentIdPlaceholder: 'Номер ученика', studentLoginBtn: 'Войти',
      backToSite: 'На сайт', site: 'Сайт', result: 'Результат', submitExam: 'Сдать',
    },
    en: {
      home: 'Home', countries: 'Countries', quiz: 'Quiz', courses: 'Courses',
      leaderboard: 'Leaderboard', profile: 'Profile', student: 'Student', login: 'Login',
      logout: 'Log out', settings: 'Settings', language: 'Language', theme: 'Theme',
      dark: 'Dark', light: 'Light', search: 'Search', loading: 'Loading…',
      error: 'Error', save: 'Save', cancel: 'Cancel', delete: 'Delete', edit: 'Edit',
      create: 'Create', back: 'Back', next: 'Next', previous: 'Previous',
      submit: 'Submit', yes: 'Yes', no: 'No', of: 'of', questions: 'questions',
      question: 'Question', questionLabel: 'Question', passScore: 'Pass',
      minutes: 'min', noLimit: 'No limit', timeUp: 'Time is up.',
      yourScore: 'Your score', submitted: 'Submitted', leaveExam: 'Leave exam?',
      noQuestions: 'No questions found.', startExam: 'Start',
      statusParticipated: 'You have already participated', questionsCount: 'Questions',
      questionXofY: 'Question {n} / {total}', writeAnswerPlaceholder: 'Write your answer...',
      noQuestion: 'No question', activeOlympiads: 'Active olympiads',
      quizzesSection: 'Quizzes', noActiveOlympiad: 'No active olympiads.',
      noQuizzesStudent: 'No quizzes.', studentLoginTitle: 'Student login',
      studentLoginHint: 'Only the ID issued by admin', studentIdLabel: 'Your ID',
      studentIdPlaceholder: 'Student number', studentLoginBtn: 'Sign in',
      backToSite: 'Back to site', site: 'Site', result: 'Result', submitExam: 'Submit',
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
      if (val === key && el.textContent && el.textContent.trim() && el.textContent.trim() !== key) {
        return;
      }
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        if (!el.getAttribute('data-i18n-value')) el.placeholder = val;
        else el.value = val;
      } else el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-placeholder], [data-pf-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder') || el.getAttribute('data-pf-placeholder');
      el.placeholder = t(key);
    });
  }

  global.GeoI18n = { t: t, setLang: setLang, lang: lang, apply: apply, DICT: DICT };
  global.t = t;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setLang(lang());
    });
  } else {
    setLang(lang());
  }
})(typeof window !== 'undefined' ? window : globalThis);
