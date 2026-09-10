// Student portal — olympiad UI (aligned with student.html IDs)
(function () {
  'use strict';

  const API = '';
  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function t(key, params) {
    var fallback = {
      previous: '\u2190 \u041f\u0435\u0448\u0442\u0430\u0440',
      next: '\u0411\u0430\u044a\u0434\u04e3 \u2192',
      submitExam: '\u0421\u0443\u043f\u043e\u0440\u0438\u0434\u0430\u043d',
      logout: '\u0411\u0430\u0440\u043e\u043c\u0430\u0434\u0430\u043d',
      back: '\u0411\u043e\u0437\u0433\u0430\u0448\u0442',
      startExam: '\u041e\u0493\u043e\u0437',
      statusParticipated: '\u0418\u0448\u0442\u0438\u0440\u043e\u043a \u043a\u0430\u0440\u0434\u0435\u0434',
      questionsCount: '\u0421\u0430\u0432\u043e\u043b\u04b3\u043e',
      minutes: '\u0434\u0430\u049b',
      noLimit: '\u0411\u0435 \u043c\u0430\u04b3\u0434\u0443\u0434\u0438\u044f\u0442',
      timeUp: '\u0412\u0430\u049b\u0442 \u0442\u0430\u043c\u043e\u043c \u0448\u0443\u0434.',
      yourScore: '\u0425\u043e\u043b\u0438 \u0448\u0443\u043c\u043e',
      submitted: '\u0421\u0443\u043f\u043e\u0440\u0438\u0434\u0430 \u0448\u0443\u0434',
      leaveExam: '\u0410\u0437 \u0438\u043c\u0442\u0438\u04b3\u043e\u043d \u0431\u0430\u0440\u043e\u043c\u0430\u0434\u0430\u043d?',
      noQuestions: '\u0421\u0430\u0432\u043e\u043b\u04b3\u043e \u0451\u0444\u0442 \u043d\u0430\u0448\u0443\u0434\u0430\u043d\u0434.',
      questionLabel: '\u0421\u0430\u0432\u043e\u043b',
      question: '\u0421\u0430\u0432\u043e\u043b',
      questionXofY: '\u0421\u0430\u0432\u043e\u043b {n} / {total}'
    };
    var s = null;
    try {
      if (window.GeoI18n && typeof window.GeoI18n.t === 'function') {
        s = window.GeoI18n.t(key, params);
      } else if (typeof window.t === 'function' && window.t !== t) {
        s = window.t(key, params);
      }
    } catch (e) { s = null; }
    if (s == null || s === '' || s === key) {
      s = fallback[key] != null ? fallback[key] : key;
    }
    if (params && typeof s === 'string') {
      Object.keys(params).forEach(function (k) {
        s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), String(params[k]));
      });
    }
    return s;
  }

  // PLACEHOLDER_REST - will be replaced
  console.log('partial');
})();
