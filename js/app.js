const API_URL = 'https://restcountries.com/v3.1/all?fields=name,capital,region,subregion,population,area,flags,cca2,cca3,latlng';
const LOCAL_COUNTRIES_URL = 'data/countries.json';
const LOCAL_COUNTRY_NAMES_TG_URL = 'data/country-names-tg.json';
const LOCAL_COUNTRIES_FULL_URL = 'data/countries-full.json';
const AUTH_API_BASE = window.location.port === '5000' ? '' : 'http://127.0.0.1:5000';
const REMOTE_COUNTRY_FIELD_GROUPS = [
    'name,capital,region,subregion,population,area,flags,cca2,cca3,latlng',
    'cca3,capitalInfo,landlocked,unMember,independent,tld,idd,currencies,languages,borders',
    'cca3,timezones,demonyms,translations,maps,continents,car,startOfWeek',
];
const COUNTRY_GEOJSON_BASE_URL = 'https://raw.githubusercontent.com/johan/world.geo.json/master/countries';

const resultsGrid = document.getElementById('results');
const alertBox = document.getElementById('alertBox');
const searchInput = document.getElementById('searchInput');
const filterRegion = document.getElementById('filterRegion');
const filterSubregion = document.getElementById('filterSubregion');
const sortSelect = document.getElementById('sortSelect');
const resetBtn = document.getElementById('resetBtn');
const modal = document.getElementById('detailModal');
const closeModalButton = document.getElementById('closeModal');
const modalTitle = document.getElementById('modalTitle');
const modalSubtitle = document.getElementById('modalSubtitle');
const modalBody = document.getElementById('modalBody');
const settingsPanel = document.querySelector('.settings-panel');
const settingsToggle = document.getElementById('settingsToggle');
const booksToggle = document.getElementById('booksToggle');
const booksModal = document.getElementById('booksModal');
const closeBooksModalButton = document.getElementById('closeBooksModal');
const booksList = document.getElementById('booksList');
const bookDetails = document.getElementById('bookDetails');
const quizToggle = document.getElementById('quizToggle');
const quizModal = document.getElementById('quizModal');
const closeQuizModalButton = document.getElementById('closeQuizModal');
const quizLocked = document.getElementById('quizLocked');
const quizLoginBtn = document.getElementById('quizLoginBtn');
const quizApp = document.getElementById('quizApp');
const quizStage = document.getElementById('quizStage');
const quizScoreboard = document.getElementById('quizScoreboard');
const friendNameInput = document.getElementById('friendNameInput');
const startQuizBtn = document.getElementById('startQuizBtn');
const resetQuizBtn = document.getElementById('resetQuizBtn');
const quizModeButtons = document.querySelectorAll('[data-quiz-mode]');
const authToggle = document.getElementById('authToggle');
const authToggleText = document.getElementById('authToggleText');
const authToggleIcon = document.getElementById('authToggleIcon');
const authModal = document.getElementById('authModal');
const closeAuthModalButton = document.getElementById('closeAuthModal');
const authMessage = document.getElementById('authMessage');
const authLoggedOut = document.getElementById('authLoggedOut');
const authLoggedIn = document.getElementById('authLoggedIn');
const authStatusBadge = document.getElementById('authStatusBadge');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const logoutBtn = document.getElementById('logoutBtn');
const authUserName = document.getElementById('authUserName');
const authUserEmail = document.getElementById('authUserEmail');
const languageSelect = document.getElementById('languageSelect');
const themeButtons = document.querySelectorAll('[data-theme-option]');

const TRANSLATIONS = {
    tg: {
        locale: 'tg-TJ',
        settingsTitle: 'Настройка',
        themeLabel: 'Ранг',
        darkMode: 'Торик',
        lightMode: 'Равшан',
        languageLabel: 'Забон',
        heroTitle: 'Географияи ҷаҳон',
        heroText: 'Сайти интерактивӣ бо ҳамаи кишварҳо, маълумоти муфассал ва харита.',
        searchLabel: 'Ҷустуҷӯи зуд',
        searchPlaceholder: 'Номи кишвар, пойтахт ё минтақа...',
        regionLabel: 'Минтақа',
        subregionLabel: 'Субминтақа',
        sortLabel: 'Сортировка',
        allRegions: 'Ҳама минтақаҳо',
        allSubregions: 'Ҳама субминтақаҳо',
        sortName: 'Ном (A → Z)',
        sortPopulation: 'Аҳолӣ (зиёд → кам)',
        sortArea: 'Масоҳат (зиёд → кам)',
        resetButton: 'Тозакунӣ',
        modalBadge: 'Маълумоти мукаммал',
        closeModal: 'Бастан',
        capital: 'Пойтахт',
        region: 'Минтақа',
        population: 'Аҳолӣ',
        area: 'Масоҳат',
        officialName: 'Номи расмӣ',
        subregion: 'Субминтақа',
        independent: 'Истиқлолият',
        unMember: 'Узви СММ',
        tld: 'Домени интернетӣ',
        callingCodes: 'Рамзи телефон',
        map: 'Харита',
        borders: 'Марзҳои давлатӣ',
        coordinates: 'Координатаҳо',
        timezones: 'Минтақаҳои вақт',
        continents: 'Қитъаҳо',
        drivingSide: 'Самти ҳаракат',
        landlocked: 'Бе баҳр',
        density: 'Зичӣ',
        demonym: 'Номи шаҳрвандон',
        languages: 'Забонҳо',
        currencies: 'Асъор',
        yes: 'Бале',
        no: 'Не',
        unknown: '—',
        km2: 'км²',
        perKm2: '/ км²',
        loading: 'Кишварҳо бор мешаванд...',
        loaded: 'Ҳамаи кишварҳо бор шуданд.',
        loadError: 'Хато: кишварҳо бор нашуданд. Лутфан дубора санҷед.',
        loadErrorState: 'Хато ҳангоми боркунии маълумот. Санҷед, ки ба интернет пайваст ҳастед.',
        emptyState: 'Кишвар ёфт нашуд. Лутфан филтрҳоро тағйир диҳед ё тавассути ҷустуҷӯ баъдтар санҷед.',
        noCoordinates: 'Координатаҳо дастрас нест, харита нишон дода намешавад.',
        generalInfo: '1. Маълумоти умумӣ',
        geography: '2. Ҷуғрофия',
        populationSection: '3. Аҳолӣ',
        economy: '4. Иқтисод',
        government: '5. Сиёсат ва давлатдорӣ',
        military: '6. Қувваи низомӣ',
        infrastructure: '7. Инфрасохтор',
        education: '8. Илм ва маориф',
        health: '9. Тандурустӣ',
        culture: '10. Фарҳанг',
        security: '11. Амният ва ҳолати дохилӣ',
        globalRole: '12. Нақши байналмилалӣ',
        pendingData: 'Маълумот дар ҳоли такмил аст.',
        flagSummary: 'Парчам ва маълумоти умумӣ',
        booksTitle: 'Китобҳои география',
        booksSubtitle: 'Китоби лозимаро интихоб кунед, баъд хонед ё насб кунед.',
        booksBadge: 'Китобхона',
        bookClass: 'Синф',
        bookYear: 'Сол',
        bookSize: 'Ҳаҷм',
        readBook: 'Хондан',
        downloadBook: 'Насб',
        authButton: 'Воридшавӣ',
        authButtonLoggedIn: 'Ҳисоб',
        authTitle: 'Ҳисоби корбар',
        authSubtitle: 'Ба сайт ворид шавед ё ҳисоби нав созед.',
        authBadge: 'Воридшавӣ',
        authBadgeLoggedIn: 'Онлайн',
        loginTitle: 'Log in',
        registerTitle: 'Регистратсия',
        nameLabel: 'Ном',
        emailLabel: 'Email',
        passwordLabel: 'Парол',
        loginButton: 'Ворид шудан',
        registerButton: 'Сабт шудан',
        logoutButton: 'Баромадан',
        loginSuccess: 'Шумо бомуваффақият ворид шудед.',
        registerSuccess: 'Ҳисоб сабт шуд ва шумо ворид шудед.',
        logoutSuccess: 'Шумо аз ҳисоб баромадед.',
        authServerError: 'Сервери сабт дастрас нест. Сайтро бо python server.py оғоз кунед.',
        quizButton: 'Викторина',
        quizTitle: 'Викторина ва худсанҷӣ',
        quizSubtitle: 'Бо дӯстатон навбат ба навбат бозӣ кунед ё худатонро санҷед.',
        quizBadge: 'Score + Time',
        quizLockedTitle: 'Аввал ворид шавед',
        quizLockedText: 'Барои викторина ва нигоҳ доштани натиҷаҳо ба ҳисоби худ ворид шавед.',
        quizSelfMode: 'Худсанҷӣ',
        quizFriendMode: 'Бо дӯст',
        friendNameLabel: 'Номи дӯст',
        friendNamePlaceholder: 'Масалан: Али',
        startQuiz: 'Оғоз',
        resetQuiz: 'Аз нав',
        nextQuestion: 'Саволи баъдӣ',
        finishQuiz: 'Анҷом',
        quizEmptyTitle: 'Тест омода аст',
        quizEmptyText: 'Ҳолатро интихоб кунед ва оғоз намоед.',
        quizQuestion: 'Савол',
        quizScore: 'Балл',
        quizTime: 'Вақт',
        quizTrue: 'Дуруст',
        quizFalse: 'Нодуруст',
        quizResult: 'Натиҷа',
        quizCorrectAnswer: 'Ҷавоби дуруст',
        quizYourAnswer: 'Ҷавоби шумо',
        quizNoAnswer: 'Ҷавоб дода нашуд',
        quizPlayerTurn: 'Навбати',
        quizFriendReady: 'Акнун дӯстатон ҷавоб медиҳад.',
        quizWinner: 'Ғолиб',
        quizDraw: 'Натиҷа баробар аст',
        quizLoginPrompt: 'Аввал ба ҳисоб ворид шавед.',
    },
    ru: {
        locale: 'ru-RU',
        settingsTitle: 'Настройки',
        themeLabel: 'Тема',
        darkMode: 'Темная',
        lightMode: 'Светлая',
        languageLabel: 'Язык',
        heroTitle: 'География мира',
        heroText: 'Интерактивный сайт со странами, подробной информацией и картой.',
        searchLabel: 'Быстрый поиск',
        searchPlaceholder: 'Название страны, столица или регион...',
        regionLabel: 'Регион',
        subregionLabel: 'Субрегион',
        sortLabel: 'Сортировка',
        allRegions: 'Все регионы',
        allSubregions: 'Все субрегионы',
        sortName: 'Название (A → Z)',
        sortPopulation: 'Население (много → мало)',
        sortArea: 'Площадь (много → мало)',
        resetButton: 'Сбросить',
        modalBadge: 'Подробная информация',
        closeModal: 'Закрыть',
        capital: 'Столица',
        region: 'Регион',
        population: 'Население',
        area: 'Площадь',
        officialName: 'Официальное название',
        subregion: 'Субрегион',
        independent: 'Независимость',
        unMember: 'Член ООН',
        tld: 'Интернет-домен',
        callingCodes: 'Телефонный код',
        map: 'Карта',
        borders: 'Границы',
        coordinates: 'Координаты',
        timezones: 'Часовые пояса',
        continents: 'Континенты',
        drivingSide: 'Сторона движения',
        landlocked: 'Без выхода к морю',
        density: 'Плотность',
        demonym: 'Жители',
        languages: 'Языки',
        currencies: 'Валюты',
        yes: 'Да',
        no: 'Нет',
        unknown: '—',
        km2: 'км²',
        perKm2: '/ км²',
        loading: 'Страны загружаются...',
        loaded: 'Все страны загружены.',
        loadError: 'Ошибка: страны не загрузились. Попробуйте еще раз.',
        loadErrorState: 'Ошибка при загрузке данных. Проверьте подключение к интернету.',
        emptyState: 'Страна не найдена. Измените фильтры или попробуйте другой поиск.',
        noCoordinates: 'Координаты недоступны, карта не будет показана.',
        generalInfo: '1. Общая информация',
        geography: '2. География',
        populationSection: '3. Население',
        economy: '4. Экономика',
        government: '5. Политика и государство',
        military: '6. Военная сила',
        infrastructure: '7. Инфраструктура',
        education: '8. Наука и образование',
        health: '9. Здравоохранение',
        culture: '10. Культура',
        security: '11. Безопасность и внутренняя ситуация',
        globalRole: '12. Международная роль',
        pendingData: 'Информация дополняется.',
        flagSummary: 'Флаг и общая информация',
        booksTitle: 'Книги по географии',
        booksSubtitle: 'Выберите нужную книгу, затем читайте или скачайте.',
        booksBadge: 'Библиотека',
        bookClass: 'Класс',
        bookYear: 'Год',
        bookSize: 'Размер',
        readBook: 'Читать',
        downloadBook: 'Скачать',
        authButton: 'Войти',
        authButtonLoggedIn: 'Аккаунт',
        authTitle: 'Аккаунт пользователя',
        authSubtitle: 'Войдите на сайт или создайте новый аккаунт.',
        authBadge: 'Вход',
        authBadgeLoggedIn: 'Онлайн',
        loginTitle: 'Log in',
        registerTitle: 'Регистрация',
        nameLabel: 'Имя',
        emailLabel: 'Email',
        passwordLabel: 'Пароль',
        loginButton: 'Войти',
        registerButton: 'Зарегистрироваться',
        logoutButton: 'Выйти',
        loginSuccess: 'Вы успешно вошли.',
        registerSuccess: 'Аккаунт создан, вы вошли.',
        logoutSuccess: 'Вы вышли из аккаунта.',
        authServerError: 'Сервер регистрации недоступен. Запустите сайт через python server.py.',
        quizButton: 'Викторина',
        quizTitle: 'Викторина и самопроверка',
        quizSubtitle: 'Играйте с другом по очереди или проверьте себя.',
        quizBadge: 'Score + Time',
        quizLockedTitle: 'Сначала войдите',
        quizLockedText: 'Войдите в аккаунт, чтобы проходить викторины и видеть результаты.',
        quizSelfMode: 'Самопроверка',
        quizFriendMode: 'С другом',
        friendNameLabel: 'Имя друга',
        friendNamePlaceholder: 'Например: Али',
        startQuiz: 'Начать',
        resetQuiz: 'Заново',
        nextQuestion: 'Следующий вопрос',
        finishQuiz: 'Завершить',
        quizEmptyTitle: 'Тест готов',
        quizEmptyText: 'Выберите режим и начните.',
        quizQuestion: 'Вопрос',
        quizScore: 'Балл',
        quizTime: 'Время',
        quizTrue: 'Верно',
        quizFalse: 'Неверно',
        quizResult: 'Результат',
        quizCorrectAnswer: 'Правильный ответ',
        quizYourAnswer: 'Ваш ответ',
        quizNoAnswer: 'Нет ответа',
        quizPlayerTurn: 'Ход',
        quizFriendReady: 'Теперь отвечает ваш друг.',
        quizWinner: 'Победитель',
        quizDraw: 'Ничья',
        quizLoginPrompt: 'Сначала войдите в аккаунт.',
    },
    en: {
        locale: 'en-US',
        settingsTitle: 'Settings',
        themeLabel: 'Theme',
        darkMode: 'Dark',
        lightMode: 'Light',
        languageLabel: 'Language',
        heroTitle: 'World Geography',
        heroText: 'An interactive website with countries, detailed information, and a map.',
        searchLabel: 'Quick Search',
        searchPlaceholder: 'Country name, capital, or region...',
        regionLabel: 'Region',
        subregionLabel: 'Subregion',
        sortLabel: 'Sort',
        allRegions: 'All regions',
        allSubregions: 'All subregions',
        sortName: 'Name (A → Z)',
        sortPopulation: 'Population (high → low)',
        sortArea: 'Area (high → low)',
        resetButton: 'Reset',
        modalBadge: 'Detailed Information',
        closeModal: 'Close',
        capital: 'Capital',
        region: 'Region',
        population: 'Population',
        area: 'Area',
        officialName: 'Official name',
        subregion: 'Subregion',
        independent: 'Independent',
        unMember: 'UN member',
        tld: 'Internet domain',
        callingCodes: 'Calling codes',
        map: 'Map',
        borders: 'Borders',
        coordinates: 'Coordinates',
        timezones: 'Time zones',
        continents: 'Continents',
        drivingSide: 'Driving side',
        landlocked: 'Landlocked',
        density: 'Density',
        demonym: 'Demonym',
        languages: 'Languages',
        currencies: 'Currencies',
        yes: 'Yes',
        no: 'No',
        unknown: '—',
        km2: 'km²',
        perKm2: '/ km²',
        loading: 'Countries are loading...',
        loaded: 'All countries loaded.',
        loadError: 'Error: countries could not be loaded. Please try again.',
        loadErrorState: 'Error loading data. Check your internet connection.',
        emptyState: 'No country found. Change the filters or try another search.',
        noCoordinates: 'Coordinates are unavailable, so the map cannot be shown.',
        generalInfo: '1. General Information',
        geography: '2. Geography',
        populationSection: '3. Population',
        economy: '4. Economy',
        government: '5. Politics and Government',
        military: '6. Military',
        infrastructure: '7. Infrastructure',
        education: '8. Science and Education',
        health: '9. Health',
        culture: '10. Culture',
        security: '11. Security and Internal Situation',
        globalRole: '12. International Role',
        pendingData: 'Information is being completed.',
        flagSummary: 'Flag and general information',
        booksTitle: 'Geography Books',
        booksSubtitle: 'Choose a book, then read it or download it.',
        booksBadge: 'Library',
        bookClass: 'Grade',
        bookYear: 'Year',
        bookSize: 'Size',
        readBook: 'Read',
        downloadBook: 'Download',
        authButton: 'Log in',
        authButtonLoggedIn: 'Account',
        authTitle: 'User Account',
        authSubtitle: 'Log in or create a new account.',
        authBadge: 'Login',
        authBadgeLoggedIn: 'Online',
        loginTitle: 'Log in',
        registerTitle: 'Register',
        nameLabel: 'Name',
        emailLabel: 'Email',
        passwordLabel: 'Password',
        loginButton: 'Log in',
        registerButton: 'Register',
        logoutButton: 'Log out',
        loginSuccess: 'You are logged in.',
        registerSuccess: 'Account created and you are logged in.',
        logoutSuccess: 'You are logged out.',
        authServerError: 'Registration server is unavailable. Start the site with python server.py.',
        quizButton: 'Quiz',
        quizTitle: 'Quiz and Self-Check',
        quizSubtitle: 'Play turn by turn with a friend or check yourself.',
        quizBadge: 'Score + Time',
        quizLockedTitle: 'Log in first',
        quizLockedText: 'Log in to take quizzes and see your results.',
        quizSelfMode: 'Self-check',
        quizFriendMode: 'With friend',
        friendNameLabel: 'Friend name',
        friendNamePlaceholder: 'Example: Ali',
        startQuiz: 'Start',
        resetQuiz: 'Reset',
        nextQuestion: 'Next question',
        finishQuiz: 'Finish',
        quizEmptyTitle: 'Test is ready',
        quizEmptyText: 'Choose a mode and start.',
        quizQuestion: 'Question',
        quizScore: 'Score',
        quizTime: 'Time',
        quizTrue: 'True',
        quizFalse: 'False',
        quizResult: 'Result',
        quizCorrectAnswer: 'Correct answer',
        quizYourAnswer: 'Your answer',
        quizNoAnswer: 'No answer',
        quizPlayerTurn: 'Turn',
        quizFriendReady: 'Now your friend answers.',
        quizWinner: 'Winner',
        quizDraw: 'Draw',
        quizLoginPrompt: 'Log in first.',
    },
};

const BOOKS = [
    {
        id: 'geo7',
        grade: '7',
        year: '2023',
        size: '12.2 MB',
        path: 'books/kitobkhon-net-geografiya-7.pdf',
        fileName: 'kitobkhon-net-geografiya-7.pdf',
        title: {
            tg: 'География, синфи 7',
            ru: 'География, 7 класс',
            en: 'Geography, Grade 7',
        },
        description: {
            tg: 'Китоби дарсӣ барои оғози омӯзиши география: табиат, харита, материкҳо ва робитаи инсон бо муҳит.',
            ru: 'Учебник для начала изучения географии: природа, карта, материки и связь человека с окружающей средой.',
            en: 'A textbook for beginning geography: nature, maps, continents, and the connection between people and the environment.',
        },
    },
    {
        id: 'geo8',
        grade: '8',
        year: '2014',
        size: '2.6 MB',
        path: 'books/kitobkhon-net-8.-geografiya-2014.pdf',
        fileName: 'kitobkhon-net-8.-geografiya-2014.pdf',
        title: {
            tg: 'География, синфи 8',
            ru: 'География, 8 класс',
            en: 'Geography, Grade 8',
        },
        description: {
            tg: 'Маводи синфи 8 бо маълумот дар бораи хусусиятҳои табиӣ, аҳолӣ, минтақаҳо ва истифодаи харитаҳо.',
            ru: 'Материалы 8 класса о природных особенностях, населении, регионах и использовании карт.',
            en: 'Grade 8 material about natural features, population, regions, and map use.',
        },
    },
    {
        id: 'geo9',
        grade: '9',
        year: '-',
        size: '8.4 MB',
        path: 'books/kitobkhon-net-9.-geografiya-2013.pdf',
        fileName: 'kitobkhon-net-9.-geografiya-2013.pdf',
        title: {
            tg: 'География, синфи 9',
            ru: 'География, 9 класс',
            en: 'Geography, Grade 9',
        },
        description: {
            tg: 'Китоб барои омӯзиши амиқтари географияи иқтисодӣ, аҳолӣ, захираҳо ва минтақаҳои муҳим.',
            ru: 'Учебник для более глубокого изучения экономической географии, населения, ресурсов и важных регионов.',
            en: 'A textbook for deeper study of economic geography, population, resources, and important regions.',
        },
    },
    {
        id: 'geo10',
        grade: '10',
        year: '2022',
        size: '15.6 MB',
        path: 'books/kitobkhon-net-geografiya-10.pdf',
        fileName: 'kitobkhon-net-geografiya-10.pdf',
        title: {
            tg: 'География, синфи 10',
            ru: 'География, 10 класс',
            en: 'Geography, Grade 10',
        },
        description: {
            tg: 'Китоби синфи 10 барои таҳлили давлатҳо, иқтисодиёт, захираҳо, нақлиёт ва робитаҳои ҷаҳонӣ.',
            ru: 'Книга 10 класса для анализа стран, экономики, ресурсов, транспорта и мировых связей.',
            en: 'A Grade 10 book for analyzing countries, economies, resources, transport, and global connections.',
        },
    },
    {
        id: 'geo11',
        grade: '11',
        year: '2015',
        size: '17.3 MB',
        path: 'books/kitobkhon-net-11.-geografiya-2015.pdf',
        fileName: 'kitobkhon-net-11.-geografiya-2015.pdf',
        title: {
            tg: 'География, синфи 11',
            ru: 'География, 11 класс',
            en: 'Geography, Grade 11',
        },
        description: {
            tg: 'Китоби ҷамъбастӣ барои синфи 11: кишварҳо, равандҳои ҷаҳонӣ, иқтисоди байналмилалӣ ва масъалаҳои муосир.',
            ru: 'Итоговая книга для 11 класса: страны, мировые процессы, международная экономика и современные вопросы.',
            en: 'A final Grade 11 book covering countries, global processes, international economics, and modern issues.',
        },
    },
];

const QUIZ_QUESTIONS = [
    {
        question: {
            tg: 'Пойтахти Тоҷикистон кадом шаҳр аст?',
            ru: 'Какой город является столицей Таджикистана?',
            en: 'Which city is the capital of Tajikistan?',
        },
        options: {
            tg: ['Душанбе', 'Хуҷанд', 'Кӯлоб', 'Бохтар'],
            ru: ['Душанбе', 'Худжанд', 'Куляб', 'Бохтар'],
            en: ['Dushanbe', 'Khujand', 'Kulob', 'Bokhtar'],
        },
        answer: 0,
    },
    {
        question: {
            tg: 'Кадом қитъа аз рӯи масоҳат калонтарин аст?',
            ru: 'Какой материк самый большой по площади?',
            en: 'Which continent is the largest by area?',
        },
        options: {
            tg: ['Осиё', 'Африқо', 'Аврупо', 'Амрикои Ҷанубӣ'],
            ru: ['Азия', 'Африка', 'Европа', 'Южная Америка'],
            en: ['Asia', 'Africa', 'Europe', 'South America'],
        },
        answer: 0,
    },
    {
        question: {
            tg: 'Дарёи дарозтарини ҷаҳон кадом аст?',
            ru: 'Какая река считается самой длинной в мире?',
            en: 'Which river is commonly considered the longest in the world?',
        },
        options: {
            tg: ['Нил', 'Амазонка', 'Янтсзи', 'Миссисипи'],
            ru: ['Нил', 'Амазонка', 'Янцзы', 'Миссисипи'],
            en: ['Nile', 'Amazon', 'Yangtze', 'Mississippi'],
        },
        answer: 0,
    },
    {
        question: {
            tg: 'Кадом кишвар аҳолии бештар дорад?',
            ru: 'Какая страна имеет самое большое население?',
            en: 'Which country has the largest population?',
        },
        options: {
            tg: ['Ҳиндустон', 'Чин', 'ИМА', 'Индонезия'],
            ru: ['Индия', 'Китай', 'США', 'Индонезия'],
            en: ['India', 'China', 'United States', 'Indonesia'],
        },
        answer: 0,
    },
    {
        question: {
            tg: 'Саҳрои калонтарини гарм дар ҷаҳон кадом аст?',
            ru: 'Какая самая большая жаркая пустыня в мире?',
            en: 'What is the largest hot desert in the world?',
        },
        options: {
            tg: ['Саҳрои Кабир', 'Гоби', 'Қарақум', 'Калахари'],
            ru: ['Сахара', 'Гоби', 'Каракумы', 'Калахари'],
            en: ['Sahara', 'Gobi', 'Karakum', 'Kalahari'],
        },
        answer: 0,
    },
    {
        question: {
            tg: 'Қуллаи баландтарини ҷаҳон кадом аст?',
            ru: 'Какая вершина самая высокая в мире?',
            en: 'Which is the highest mountain peak in the world?',
        },
        options: {
            tg: ['Эверест', 'К2', 'Исмоили Сомонӣ', 'Килиманҷаро'],
            ru: ['Эверест', 'К2', 'Пик Исмоила Сомони', 'Килиманджаро'],
            en: ['Everest', 'K2', 'Ismoil Somoni Peak', 'Kilimanjaro'],
        },
        answer: 0,
    },
];

const REGION_TRANSLATIONS = {
    tg: {
        Africa: 'Африқо',
        Americas: 'Амрико',
        Antarctic: 'Антарктида',
        Antarctica: 'Антарктида',
        Asia: 'Осиё',
        Europe: 'Аврупо',
        Oceania: 'Уқёнусия',
    },
    ru: {
        Africa: 'Африка',
        Americas: 'Америка',
        Antarctic: 'Антарктика',
        Antarctica: 'Антарктика',
        Asia: 'Азия',
        Europe: 'Европа',
        Oceania: 'Океания',
    },
};

const SUBREGION_TRANSLATIONS = {
    tg: {
        'Australia and New Zealand': 'Австралия ва Зеландияи Нав',
        Caribbean: 'Ҳавзаи Кариб',
        'Central America': 'Амрикои Марказӣ',
        'Central Asia': 'Осиёи Марказӣ',
        'Central Europe': 'Аврупои Марказӣ',
        'Eastern Africa': 'Африқои Шарқӣ',
        'Eastern Asia': 'Осиёи Шарқӣ',
        'Eastern Europe': 'Аврупои Шарқӣ',
        Melanesia: 'Меланезия',
        Micronesia: 'Микронезия',
        'Middle Africa': 'Африқои Марказӣ',
        'North America': 'Амрикои Шимолӣ',
        'Northern Africa': 'Африқои Шимолӣ',
        'Northern Europe': 'Аврупои Шимолӣ',
        Polynesia: 'Полинезия',
        'South America': 'Амрикои Ҷанубӣ',
        'South-Eastern Asia': 'Осиёи Ҷанубу Шарқӣ',
        'Southeast Europe': 'Аврупои Ҷанубу Шарқӣ',
        'Southern Africa': 'Африқои Ҷанубӣ',
        'Southern Asia': 'Осиёи Ҷанубӣ',
        'Southern Europe': 'Аврупои Ҷанубӣ',
        'Western Africa': 'Африқои Ғарбӣ',
        'Western Asia': 'Осиёи Ғарбӣ',
        'Western Europe': 'Аврупои Ғарбӣ',
    },
    ru: {
        'Australia and New Zealand': 'Австралия и Новая Зеландия',
        Caribbean: 'Карибский бассейн',
        'Central America': 'Центральная Америка',
        'Central Asia': 'Центральная Азия',
        'Central Europe': 'Центральная Европа',
        'Eastern Africa': 'Восточная Африка',
        'Eastern Asia': 'Восточная Азия',
        'Eastern Europe': 'Восточная Европа',
        Melanesia: 'Меланезия',
        Micronesia: 'Микронезия',
        'Middle Africa': 'Центральная Африка',
        'North America': 'Северная Америка',
        'Northern Africa': 'Северная Африка',
        'Northern Europe': 'Северная Европа',
        Polynesia: 'Полинезия',
        'South America': 'Южная Америка',
        'South-Eastern Asia': 'Юго-Восточная Азия',
        'Southeast Europe': 'Юго-Восточная Европа',
        'Southern Africa': 'Южная Африка',
        'Southern Asia': 'Южная Азия',
        'Southern Europe': 'Южная Европа',
        'Western Africa': 'Западная Африка',
        'Western Asia': 'Западная Азия',
        'Western Europe': 'Западная Европа',
    },
};

const LANGUAGE_NAME_TRANSLATIONS = {
    tg: {
        English: 'англисӣ',
        Russian: 'русӣ',
        Tajik: 'тоҷикӣ',
        Arabic: 'арабӣ',
        Spanish: 'испанӣ',
        French: 'фаронсавӣ',
        German: 'немисӣ',
        Portuguese: 'португалӣ',
        Chinese: 'чинӣ',
        Persian: 'форсӣ',
        Uzbek: 'узбекӣ',
        Turkish: 'туркӣ',
        Hindi: 'ҳиндӣ',
    },
    ru: {
        English: 'английский',
        Russian: 'русский',
        Tajik: 'таджикский',
        Arabic: 'арабский',
        Spanish: 'испанский',
        French: 'французский',
        German: 'немецкий',
        Portuguese: 'португальский',
        Chinese: 'китайский',
        Persian: 'персидский',
        Uzbek: 'узбекский',
        Turkish: 'турецкий',
        Hindi: 'хинди',
    },
};

const CCA3_TO_CCA2 = {
    AFG: 'AF',
};

let regionDisplayNames = {};

try {
    regionDisplayNames = {
        tg: new Intl.DisplayNames(['tg'], { type: 'region' }),
        ru: new Intl.DisplayNames(['ru'], { type: 'region' }),
        en: new Intl.DisplayNames(['en'], { type: 'region' }),
    };
} catch (error) {
    regionDisplayNames = {};
}

let allCountries = [];
let activeCountries = [];
let countryNameTranslations = { tg: {} };
let countriesFullMap = {};
let activeBookId = BOOKS[0].id;
let quizMode = 'self';
let quizSession = null;
let quizTimerId = null;
let currentUser = loadStoredUser();
let currentLanguage = localStorage.getItem('siteLanguage') || 'tg';
let currentTheme = localStorage.getItem('siteTheme') || 'dark';
let detailMap = null;
let activeModalCountry = null;
let activeCountryBoundary = null;
let countryGeoJsonCache = new Map();

function t(key) {
    return TRANSLATIONS[currentLanguage]?.[key] || TRANSLATIONS.tg[key] || key;
}

function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }[char]));
}

function formatNumber(value) {
    if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) {
        return t('unknown');
    }

    return new Intl.NumberFormat(t('locale')).format(Number(value));
}

function boolText(value) {
    if (typeof value !== 'boolean') return t('unknown');
    return value ? t('yes') : t('no');
}

function normalizeLatinText(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function transliterateLatin(value, language = currentLanguage) {
    if (!value || language === 'en' || /[А-Яа-яЁёӢӣӮӯҚқҒғҲҳҶҷ]/.test(value)) {
        return value || t('unknown');
    }

    const digraphs = language === 'tg'
        ? [
            ['sch', 'ш'], ['sh', 'ш'], ['ch', 'ч'], ['zh', 'ж'], ['kh', 'х'],
            ['gh', 'ғ'], ['ts', 'тс'], ['ya', 'я'], ['yu', 'ю'], ['yo', 'ё'], ['ye', 'е'],
        ]
        : [
            ['sch', 'щ'], ['sh', 'ш'], ['ch', 'ч'], ['zh', 'ж'], ['kh', 'х'],
            ['gh', 'г'], ['ts', 'ц'], ['ya', 'я'], ['yu', 'ю'], ['yo', 'ё'], ['ye', 'е'],
        ];

    const letters = language === 'tg'
        ? {
            a: 'а', b: 'б', c: 'к', d: 'д', e: 'е', f: 'ф', g: 'г', h: 'ҳ', i: 'и',
            j: 'ҷ', k: 'к', l: 'л', m: 'м', n: 'н', o: 'о', p: 'п', q: 'қ', r: 'р',
            s: 'с', t: 'т', u: 'у', v: 'в', w: 'в', x: 'кс', y: 'й', z: 'з',
        }
        : {
            a: 'а', b: 'б', c: 'к', d: 'д', e: 'е', f: 'ф', g: 'г', h: 'х', i: 'и',
            j: 'дж', k: 'к', l: 'л', m: 'м', n: 'н', o: 'о', p: 'п', q: 'к', r: 'р',
            s: 'с', t: 'т', u: 'у', v: 'в', w: 'в', x: 'кс', y: 'й', z: 'з',
        };

    const normalized = normalizeLatinText(value);
    let output = '';
    let index = 0;

    while (index < normalized.length) {
        const slice = normalized.slice(index).toLowerCase();
        const found = digraphs.find(([latin]) => slice.startsWith(latin));

        if (found) {
            output += found[1];
            index += found[0].length;
            continue;
        }

        const char = normalized[index];
        output += letters[char.toLowerCase()] || char;
        index += 1;
    }

    return output.replace(/\b\p{L}/gu, char => char.toLocaleUpperCase(language === 'ru' ? 'ru-RU' : 'tg-TJ'));
}

function getFlagCode(country) {
    const flagUrl = country.flag || country.flags?.svg || country.flags?.png || '';
    const match = String(flagUrl).match(/\/([a-z]{2})\.(?:png|svg)$/i);
    return match ? match[1].toUpperCase() : CCA3_TO_CCA2[country.cca3] || '';
}

async function loadCountryNameTranslations() {
    try {
        const response = await fetch(LOCAL_COUNTRY_NAMES_TG_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const names = await response.json();
        countryNameTranslations.tg = names || {};
    } catch (error) {
        console.warn('Tajik country names failed:', error);
        countryNameTranslations.tg = {};
    }
}

async function loadFullCountryData() {
    try {
        const response = await fetch(LOCAL_COUNTRIES_FULL_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        countriesFullMap = data || {};
    } catch (error) {
        console.warn('Full country data failed to load:', error);
        countriesFullMap = {};
    }
}

async function fetchRemoteCountries() {
    const groups = await Promise.all(REMOTE_COUNTRY_FIELD_GROUPS.map(async fields => {
        const response = await fetch(`https://restcountries.com/v3.1/all?fields=${fields}`);
        if (!response.ok) throw new Error(`REST Countries HTTP ${response.status}`);
        return response.json();
    }));
    const map = new Map();

    groups.forEach(rows => {
        rows.forEach(country => {
            map.set(country.cca3, {
                ...(map.get(country.cca3) || {}),
                ...country,
            });
        });
    });

    return Array.from(map.values());
}

function getSectionFallbackText(country, sectionKey) {
    const countryName = countryTitle(country);
    const capital = localizeCapital(country.capital);
    const region = localizeRegion(country.region);
    const population = formatNumber(country.population);
    const area = country.area > 0 ? `${formatNumber(country.area)} ${t('km2')}` : t('unknown');
    const membership = boolText(country.unMember);
    const independence = boolText(country.independent);
    const languages = localizeDelimitedText(country.languages);
    const currencies = localizeDelimitedText(country.currencies);

    const fallbacks = {
        economy: {
            tg: `${countryName} дорои аҳолӣ ${population} ва масоҳат ${area} мебошад. Иқтисодиёти он асосан ба савдо, хизматрасонӣ ва захираҳои маҳаллии минтақа такя мекунад.`,
            ru: `Экономика ${countryName} формируется населением ${population} и площадью ${area}, а также опирается на торговлю, услуги и региональные ресурсы.`,
            en: `The economy of ${countryName} is shaped by its population of ${population} and area of ${area}, with trade, services and regional resources playing an important role.`,
        },
        government: {
            tg: `${countryName} ташкилёфта ҳамчун давлати соҳибихтиёр дар минтақаи ${region} бо мақоми мустақил ва узвияти ${membership} дар Созмони Милали Муттаҳид аст.`,
            ru: `${countryName} является суверенным государством в регионе ${region} с независимым статусом и членством ООН: ${membership}.`,
            en: `${countryName} is a sovereign state in the ${region} region with independent status and UN membership: ${membership}.`,
        },
        military: {
            tg: `Ҳифзи амният ва субот тавассути қувваҳои мусаллаҳ ва мақомоти дахлдор дар ${countryName} иҷро мешавад.`,
            ru: `Оборона и безопасность обеспечиваются вооруженными силами и компетентными органами ${countryName}.`,
            en: `Defense and security in ${countryName} are maintained by the armed forces and national authorities.`,
        },
        infrastructure: {
            tg: `Инфрасохтор дар ${countryName} ба нақлиёт, нерӯ ва алоқа ҳамроҳ мешавад, ки рушди иқтисод ва зиндагии ҷомеаро таҳрик медиҳад.`,
            ru: `Инфраструктура ${countryName} включает транспорт, электроэнергию и связь, поддерживающие экономику и общественную жизнь.`,
            en: `Infrastructure in ${countryName} covers transport, energy and communications, supporting the economy and daily life.`,
        },
        education: {
            tg: `Система маориф дар ${countryName} таблиғоти ибтидоии умумӣ, миёна ва олиро дар бар мегирад.`,
            ru: `Система образования ${countryName} охватывает начальное, среднее и высшее обучение.`,
            en: `The education system in ${countryName} includes primary, secondary and higher education.`,
        },
        health: {
            tg: `Хизматрасонии тиббӣ дар ${countryName} тавассути муассисаҳои давлатӣ ва хусусӣ пешниҳод мешавад, то саломатии аҳолиро ҳифз кунад.`,
            ru: `Медицинские услуги в ${countryName} предоставляются государственными и частными учреждениями для защиты здоровья населения.`,
            en: `Healthcare in ${countryName} is delivered through public and private providers to protect the population's health.`,
        },
        culture: {
            tg: `${countryName} дорои мероси фарҳангӣ, забонҳо ва анъанаҳои устувор аст, ки шахсияту ҳувияти онро муайян мекунад.`,
            ru: `${countryName} имеет богатое культурное наследие, языки и традиции, определяющие его идентичность.`,
            en: `${countryName} has a rich cultural heritage, languages and traditions that define its identity.`,
        },
        security: {
            tg: `Амният дар ${countryName} тавассути қонунгузорӣ, мақомоти ҳифзи ҳуқуқ ва назорати марз таъмин карда мешавад.`,
            ru: `Безопасность в ${countryName} обеспечивается законодательством, правоохранительными органами и контролем границ.`,
            en: `Security in ${countryName} is upheld through law enforcement, legislation and border control.`,
        },
        globalRole: {
            tg: `${countryName} дар муносибатҳои минтақавӣ ва байналмилалӣ фаъолият мекунад ва дар доираи Созмони Милал иштирок мекунад.`,
            ru: `${countryName} участвует в региональных и международных отношениях и является членом ООН.`,
            en: `${countryName} engages in regional and international relations and is a member of the UN.`,
        },
        independence: {
            tg: independence === t('yes')
                ? `${countryName} як давлати соҳибихтиёр аст ва мустақил мебошад.`
                : `${countryName} ҳангоми мавҷудӣ ҳамчун давлати мустақил баррасӣ мешавад.`,
            ru: independence === t('yes')
                ? `${countryName} является суверенным независимым государством.`
                : `${countryName} рассматривается как независимое государство.`,
            en: independence === t('yes')
                ? `${countryName} is a sovereign independent state.`
                : `${countryName} is considered an independent country.`,
        },
    };

    return fallbacks[sectionKey]?.[currentLanguage] || null;
}

function getFullSectionText(country, sectionKey) {
    if (!country || !country.cca3) return getSectionFallbackText(country, sectionKey);
    const full = countriesFullMap[country.cca3] || countriesFullMap[country.raw?.cca3] || countriesFullMap[country.cca2] || null;
    if (!full) return getSectionFallbackText(country, sectionKey);
    const val = full[sectionKey];
    if (!val) return getSectionFallbackText(country, sectionKey);
    if (typeof val === 'string') return val;
    return val[currentLanguage] || val.tg || val.ru || val.en || getSectionFallbackText(country, sectionKey);
}

function getCountryFact(country, key) {
    const value = country?.[key] || country?.raw?.[key];
    if (Array.isArray(value)) return value.length ? value.join(', ') : t('unknown');
    return value || t('unknown');
}

function getTldText(country) {
    if (country.tld && country.tld !== t('unknown')) return country.tld;
    if (country.cca3 === 'UNK') {
        return {
            tg: '.xk (ғайрирасмӣ)',
            ru: '.xk (неофициально)',
            en: '.xk (unofficial)',
        }[currentLanguage];
    }
    return t('unknown');
}

function getCallingCodesText(country) {
    if (country.callingCodes && country.callingCodes !== t('unknown')) return country.callingCodes;
    if (country.cca3 === 'ATA' || country.cca3 === 'HMD') {
        return {
            tg: 'Рамзи ягонаи давлатӣ надорад',
            ru: 'Единого государственного кода нет',
            en: 'No single country calling code',
        }[currentLanguage];
    }
    return t('unknown');
}

function getBorderCount(country) {
    return Array.isArray(country.raw?.borders) ? country.raw.borders.length : 0;
}

function getStatusText(country) {
    const independent = boolText(country.independent);
    const unMember = boolText(country.unMember);

    return {
        tg: `${countryTitle(country)} ${country.independent ? 'давлати соҳибихтиёр' : 'ҳудуд ё минтақаи махсус'} мебошад. Узвият дар СММ: ${unMember}. Истиқлолият: ${independent}.`,
        ru: `${countryTitle(country)} является ${country.independent ? 'суверенным государством' : 'территорией или особым регионом'}. Членство в ООН: ${unMember}. Независимость: ${independent}.`,
        en: `${countryTitle(country)} is ${country.independent ? 'a sovereign country' : 'a territory or special region'}. UN membership: ${unMember}. Independence: ${independent}.`,
    }[currentLanguage];
}

function getSectionFallbackText(country, sectionKey) {
    const countryName = countryTitle(country);
    const capital = localizeCapital(country.capital);
    const region = localizeRegion(country.region);
    const subregion = localizeSubregion(country.subregion);
    const population = formatNumber(country.population);
    const area = country.area > 0 ? `${formatNumber(country.area)} ${t('km2')}` : t('unknown');
    const density = country.area > 0 ? `${formatNumber((country.population / country.area).toFixed(2))} ${t('perKm2')}` : t('unknown');
    const languages = localizeDelimitedText(country.languages);
    const currencies = localizeDelimitedText(country.currencies);
    const borders = getBordersText(country);
    const borderCount = getBorderCount(country);
    const timezones = getCountryFact(country, 'timezones');
    const continents = getCountryFact(country, 'continents');
    const tld = getTldText(country);
    const callingCodes = getCallingCodesText(country);
    const landlocked = boolText(country.landlocked);

    const templates = {
        economy: {
            tg: `${countryName} дорои аҳолии ${population}, масоҳати ${area} ва зичии аҳолии ${density} мебошад. Иқтисоди кишвар ба захираҳои маҳаллӣ, савдо, хизматрасонӣ ва робитаҳои минтақавӣ такя мекунад; асъори истифодашаванда: ${currencies}. Пойтахт, яъне ${capital}, яке аз марказҳои асосии иқтисодӣ ва маъмурӣ ба ҳисоб меравад.`,
            ru: `${countryName} имеет население ${population}, площадь ${area} и плотность ${density}. Экономика опирается на местные ресурсы, торговлю, услуги и региональные связи; используемая валюта: ${currencies}. Столица ${capital} является одним из главных экономических и административных центров.`,
            en: `${countryName} has a population of ${population}, an area of ${area}, and a density of ${density}. Its economy relies on local resources, trade, services, and regional connections; currency: ${currencies}. The capital, ${capital}, is one of the main economic and administrative centers.`,
        },
        government: {
            tg: `${getStatusText(country)} Пойтахти кишвар ${capital} аст. Минтақа: ${region}; субминтақа: ${subregion}. Домени интернетӣ: ${tld}; рамзи телефон: ${callingCodes}.`,
            ru: `${getStatusText(country)} Столица: ${capital}. Регион: ${region}; субрегион: ${subregion}. Интернет-домен: ${tld}; телефонный код: ${callingCodes}.`,
            en: `${getStatusText(country)} Capital: ${capital}. Region: ${region}; subregion: ${subregion}. Internet domain: ${tld}; calling code: ${callingCodes}.`,
        },
        military: {
            tg: `Амният ва мудофиаи ${countryName} ба ҳифзи марзҳо, тартиботи дохилӣ ва ҳамкории минтақавӣ вобаста аст. Кишвар бо ${borderCount} ҳамсоя марзи заминӣ дорад; ҳолати бе баҳр будан: ${landlocked}. Ин омилҳо барои назорати сарҳад ва нақлиёт аҳамияти калон доранд.`,
            ru: `Безопасность и оборона ${countryName} связаны с охраной границ, внутренним порядком и региональным сотрудничеством. Сухопутных соседей: ${borderCount}; отсутствие выхода к морю: ${landlocked}. Эти факторы важны для пограничного контроля и транспорта.`,
            en: `Security and defense in ${countryName} are tied to border protection, internal order, and regional cooperation. Land-border neighbors: ${borderCount}; landlocked: ${landlocked}. These factors matter for border control and transport.`,
        },
        infrastructure: {
            tg: `Инфрасохтори ${countryName} аз шабакаҳои нақлиётӣ, алоқа, марказҳои маъмурӣ ва хизматрасонии ҷамъиятӣ иборат аст. Пойтахт ${capital} нақши марказӣ дорад. Минтақаҳои вақт: ${timezones}; рамзи телефон: ${callingCodes}; домени интернетӣ: ${tld}.`,
            ru: `Инфраструктура ${countryName} включает транспортные сети, связь, административные центры и общественные услуги. Столица ${capital} играет центральную роль. Часовые пояса: ${timezones}; телефонный код: ${callingCodes}; интернет-домен: ${tld}.`,
            en: `Infrastructure in ${countryName} includes transport networks, communications, administrative centers, and public services. The capital ${capital} plays a central role. Time zones: ${timezones}; calling code: ${callingCodes}; internet domain: ${tld}.`,
        },
        education: {
            tg: `Маориф дар ${countryName} ба омӯзиши ибтидоӣ, миёна ва олӣ такя мекунад. Забонҳои асосӣ: ${languages}. Марказҳои калон, махсусан ${capital}, барои муассисаҳои таълимӣ ва илмӣ аҳамияти муҳим доранд.`,
            ru: `Образование в ${countryName} включает начальное, среднее и высшее обучение. Основные языки: ${languages}. Крупные центры, особенно ${capital}, важны для образовательных и научных учреждений.`,
            en: `Education in ${countryName} includes primary, secondary, and higher learning. Main languages: ${languages}. Major centers, especially ${capital}, are important for educational and scientific institutions.`,
        },
        health: {
            tg: `Системаи тандурустии ${countryName} ба хизматрасонии аҳолии ${population} равона шудааст. Хизматрасониҳои асосӣ дар шаҳрҳои калон ва пойтахт ${capital} мутамарказ мешаванд, дар минтақаҳо бошад дастрасӣ ба инфрасохтор ва нақлиёт нақши муҳим мебозад.`,
            ru: `Система здравоохранения ${countryName} обслуживает население ${population}. Основные услуги сосредоточены в крупных городах и столице ${capital}, а в регионах важную роль играют инфраструктура и транспортная доступность.`,
            en: `Healthcare in ${countryName} serves a population of ${population}. Core services are concentrated in major cities and the capital ${capital}, while infrastructure and transport access are important in regional areas.`,
        },
        culture: {
            tg: `${countryName} дар минтақаи ${region} ҷойгир буда, мероси фарҳангӣ, забонҳо ва анъанаҳои худро дорад. Забонҳои асосӣ: ${languages}. Ҷойгиршавӣ дар ${subregion} ба робитаҳои таърихӣ ва фарҳангии кишвар таъсир мерасонад.`,
            ru: `${countryName} расположен(а) в регионе ${region} и имеет собственное культурное наследие, языки и традиции. Основные языки: ${languages}. Положение в ${subregion} влияет на исторические и культурные связи страны.`,
            en: `${countryName} is located in ${region} and has its own cultural heritage, languages, and traditions. Main languages: ${languages}. Its position in ${subregion} shapes historical and cultural connections.`,
        },
        security: {
            tg: `Амнияти дохилии ${countryName} ба қонунгузорӣ, мақомоти ҳифзи ҳуқуқ ва назорати марзҳо такя мекунад. Марзҳои давлатӣ: ${borders}. Узвият дар СММ ва ҳамкориҳои минтақавӣ барои суботи кишвар аҳамият доранд.`,
            ru: `Внутренняя безопасность ${countryName} опирается на законодательство, правоохранительные органы и пограничный контроль. Государственные границы: ${borders}. Членство в ООН и региональное сотрудничество важны для стабильности.`,
            en: `Internal security in ${countryName} relies on legislation, law enforcement, and border control. Borders: ${borders}. UN membership and regional cooperation matter for stability.`,
        },
        globalRole: {
            tg: `${countryName} дар муносибатҳои минтақавӣ ва байналмилалӣ иштирок мекунад. Узвияти СММ: ${boolText(country.unMember)}. Ҷойгиршавӣ дар ${region} ва робита бо ҳамсояҳо (${borders}) барои нақши байналмилалии кишвар муҳим аст.`,
            ru: `${countryName} участвует в региональных и международных отношениях. Членство в ООН: ${boolText(country.unMember)}. Расположение в ${region} и связи с соседями (${borders}) важны для международной роли страны.`,
            en: `${countryName} participates in regional and international relations. UN membership: ${boolText(country.unMember)}. Its location in ${region} and links with neighbors (${borders}) are important for its international role.`,
        },
    };

    return templates[sectionKey]?.[currentLanguage] || templates[sectionKey]?.tg || '';
}

function getFullSectionText(country, sectionKey) {
    return getSectionFallbackText(country, sectionKey);
}

function localizeCountryName(country) {
    if (currentLanguage === 'en') return country.name.common;

    if (currentLanguage === 'tg' && countryNameTranslations.tg[country.cca3]) {
        return countryNameTranslations.tg[country.cca3];
    }

    const code = country.cca2 || getFlagCode(country);
    const displayName = code && regionDisplayNames[currentLanguage]?.of(code);

    if (displayName && displayName !== code) {
        return displayName;
    }

    if (currentLanguage === 'ru' && country.translations?.rus?.common) {
        return country.translations.rus.common;
    }

    return transliterateLatin(country.name.common);
}

function localizeRegion(value) {
    if (!value || value === t('unknown')) return t('unknown');
    if (currentLanguage === 'en') return value;
    return REGION_TRANSLATIONS[currentLanguage]?.[value] || transliterateLatin(value);
}

function localizeSubregion(value) {
    if (!value || value === t('unknown')) return t('unknown');
    if (currentLanguage === 'en') return value;
    return SUBREGION_TRANSLATIONS[currentLanguage]?.[value] || transliterateLatin(value);
}

function localizeCapital(value) {
    if (!value || value === t('unknown')) {
        return {
            tg: 'Пойтахти расмӣ надорад',
            ru: 'Официальной столицы нет',
            en: 'No official capital',
        }[currentLanguage];
    }
    return currentLanguage === 'en' ? value : transliterateLatin(value);
}

function localizeDelimitedText(value) {
    if (!value || value === t('unknown') || currentLanguage === 'en') return value || t('unknown');

    return String(value).split(',').map(item => {
        const trimmed = item.trim();
        return LANGUAGE_NAME_TRANSLATIONS[currentLanguage]?.[trimmed] || transliterateLatin(trimmed);
    }).join(', ');
}

function localizeContinents(value) {
    if (!value || value === t('unknown')) return t('unknown');
    return String(value).split(',').map(item => localizeRegion(item.trim())).join(', ');
}

function localizeDrivingSide(value) {
    if (!value || value === t('unknown')) return t('unknown');
    const sides = {
        left: { tg: 'чап', ru: 'слева', en: 'left' },
        right: { tg: 'рост', ru: 'справа', en: 'right' },
    };
    return sides[String(value).toLowerCase()]?.[currentLanguage] || value;
}

function localizeDemonym(value) {
    if (!value || value === t('unknown')) {
        return {
            tg: 'Истилоҳи расмӣ дастрас нест',
            ru: 'Официальный демоним недоступен',
            en: 'Official demonym unavailable',
        }[currentLanguage];
    }
    return localizeDelimitedText(value);
}

function getBordersText(country) {
    const borderCodes = country.raw?.borders || [];
    if (!borderCodes.length) {
        return {
            tg: 'Марзи заминӣ надорад',
            ru: 'Нет сухопутных границ',
            en: 'No land borders',
        }[currentLanguage];
    }

    const names = borderCodes.map(code => {
        const neighbor = allCountries.find(item => item.cca3 === code || item.cca2 === code);
        return neighbor ? countryTitle(neighbor) : code;
    });

    return names.join(', ');
}

function showAlert(message, type = 'info', duration = 4000) {
    if (!alertBox) return;

    alertBox.textContent = message;
    alertBox.className = `alert ${type}`;
    alertBox.classList.remove('hidden');

    if (duration > 0) {
        window.clearTimeout(alertBox.dismissTimeout);
        alertBox.dismissTimeout = window.setTimeout(() => {
            alertBox.classList.add('hidden');
        }, duration);
    }
}

function getCountryName(country) {
    return localizeCountryName(country);
}

function getOfficialName(country) {
    if (currentLanguage === 'en') {
        return country.name.official || getCountryName(country);
    }

    if (currentLanguage === 'ru' && country.translations?.rus?.official) {
        return country.translations?.rus?.official || country.name.official || getCountryName(country);
    }

    return getCountryName(country);
}

function normalizeCountry(country) {
    const commonName = typeof country.name === 'string'
        ? country.name
        : country.name?.common || country.commonName || t('unknown');
    const officialName = typeof country.name === 'string'
        ? country.officialName || country.name
        : country.name?.official || country.officialName || commonName;
    const capital = Array.isArray(country.capital) ? country.capital[0] : country.capital;
    const cca2 = country.cca2 || getFlagCode(country);
    const raw = {
        ...country,
        cca2,
        name: {
            common: commonName,
            official: officialName,
        },
        translations: country.translations || {},
    };
    const currencies = typeof country.currencies === 'string'
        ? country.currencies
        : country.currencies
        ? Object.values(country.currencies).map(item => `${item.name}${item.symbol ? ` (${item.symbol})` : ''}`).join(', ')
        : '';
    const languages = typeof country.languages === 'string'
        ? country.languages
        : country.languages ? Object.values(country.languages).join(', ') : '';
    const demonym = country.demonyms?.eng?.m || country.demonyms?.eng?.f || '';
    const callingCodes = country.idd?.root
        ? (country.idd.suffixes || []).map(suffix => `${country.idd.root}${suffix}`).join(', ')
        : '';

    const searchText = [
        commonName,
        officialName,
        country.translations?.rus?.common,
        country.translations?.rus?.official,
        capital,
        country.region,
        country.subregion,
        country.cca3,
        country.cca2,
    ].filter(Boolean).join(' ').toLowerCase();

    return {
        raw,
        cca3: country.cca3 || '',
        cca2,
        flag: country.flag || country.flags?.svg || country.flags?.png || '',
        capital: capital || t('unknown'),
        region: country.region || t('unknown'),
        subregion: country.subregion || t('unknown'),
        population: country.population || 0,
        area: country.area || 0,
        latlng: Array.isArray(country.latlng) && country.latlng.length === 2 ? country.latlng : null,
        capitalCoords: Array.isArray(country.capitalCoords) && country.capitalCoords.length === 2
            ? country.capitalCoords
            : Array.isArray(country.capitalInfo?.latlng) && country.capitalInfo.latlng.length === 2 ? country.capitalInfo.latlng : null,
        landlocked: country.landlocked,
        unMember: country.unMember,
        independent: country.independent,
        tld: country.tld?.join(', ') || t('unknown'),
        callingCodes: callingCodes || t('unknown'),
        currencies: currencies || t('unknown'),
        languages: languages || t('unknown'),
        borders: country.borders?.join(', ') || t('unknown'),
        timezones: country.timezones?.join(', ') || t('unknown'),
        continents: country.continents?.join(', ') || t('unknown'),
        drivingSide: country.car?.side || t('unknown'),
        maps: country.maps || {},
        demonym: demonym || t('unknown'),
        searchText,
    };
}

function countryTitle(country) {
    return getCountryName(country.raw);
}

function countryOfficial(country) {
    return getOfficialName(country.raw);
}

function renderCountries(list) {
    if (!list.length) {
        resultsGrid.innerHTML = `<div class="empty-state">${escapeHTML(t('emptyState'))}</div>`;
        return;
    }

    resultsGrid.innerHTML = list.map(country => {
        const name = escapeHTML(countryTitle(country));
        return `
            <article class="country-card" data-cca3="${escapeHTML(country.cca3)}">
                <img class="card-flag" src="${escapeHTML(country.flag)}" alt="${name}">
                <div class="card-content">
                    <h3 class="card-title">${name}</h3>
                    <div class="card-meta">
                        <p><strong>${escapeHTML(t('capital'))}:</strong> ${escapeHTML(localizeCapital(country.capital))}</p>
                        <p><strong>${escapeHTML(t('region'))}:</strong> ${escapeHTML(localizeRegion(country.region))}</p>
                        <p><strong>${escapeHTML(t('population'))}:</strong> ${formatNumber(country.population)}</p>
                        <p><strong>${escapeHTML(t('area'))}:</strong> ${formatNumber(country.area)} ${escapeHTML(t('km2'))}</p>
                    </div>
                </div>
            </article>
        `;
    }).join('');

    document.querySelectorAll('.country-card').forEach(card => {
        card.addEventListener('click', () => {
            const country = allCountries.find(item => item.cca3 === card.dataset.cca3);
            if (country) openCountryModal(country);
        });
    });
}

function populateRegionFilters(selectedRegion = filterRegion.value || 'all') {
    const regions = Array.from(new Set(allCountries.map(country => country.region).filter(Boolean)))
        .sort((a, b) => localizeRegion(a).localeCompare(localizeRegion(b), t('locale'), { sensitivity: 'base' }));
    filterRegion.innerHTML = `<option value="all">${escapeHTML(t('allRegions'))}</option>${regions.map(region => `<option value="${escapeHTML(region)}">${escapeHTML(localizeRegion(region))}</option>`).join('')}`;
    filterRegion.value = regions.includes(selectedRegion) ? selectedRegion : 'all';
    populateSubregionFilters(filterRegion.value);
}

function populateSubregionFilters(selectedRegion = 'all', selectedSubregion = filterSubregion.value || 'all') {
    const subregions = new Set();
    allCountries.forEach(country => {
        if (selectedRegion === 'all' || country.region === selectedRegion) {
            if (country.subregion && country.subregion !== t('unknown')) subregions.add(country.subregion);
        }
    });

    const sorted = Array.from(subregions)
        .sort((a, b) => localizeSubregion(a).localeCompare(localizeSubregion(b), t('locale'), { sensitivity: 'base' }));
    filterSubregion.innerHTML = `<option value="all">${escapeHTML(t('allSubregions'))}</option>${sorted.map(sub => `<option value="${escapeHTML(sub)}">${escapeHTML(localizeSubregion(sub))}</option>`).join('')}`;
    filterSubregion.value = sorted.includes(selectedSubregion) ? selectedSubregion : 'all';
}

function applyFilters() {
    const query = searchInput.value.trim().toLowerCase();
    const selectedRegion = filterRegion.value;
    const selectedSubregion = filterSubregion.value;

    activeCountries = allCountries.filter(country => {
        if (selectedRegion !== 'all' && country.region !== selectedRegion) return false;
        if (selectedSubregion !== 'all' && country.subregion !== selectedSubregion) return false;
        if (!query) return true;

        return (
            countryTitle(country).toLowerCase().includes(query) ||
            countryOfficial(country).toLowerCase().includes(query) ||
            country.capital.toLowerCase().includes(query) ||
            localizeCapital(country.capital).toLowerCase().includes(query) ||
            localizeRegion(country.region).toLowerCase().includes(query) ||
            localizeSubregion(country.subregion).toLowerCase().includes(query) ||
            country.searchText.includes(query)
        );
    });

    applySort();
    renderCountries(activeCountries);
}

function applySort() {
    const option = sortSelect.value;

    if (option === 'population') {
        activeCountries.sort((a, b) => b.population - a.population);
    } else if (option === 'area') {
        activeCountries.sort((a, b) => b.area - a.area);
    } else {
        activeCountries.sort((a, b) => countryTitle(a).localeCompare(countryTitle(b), t('locale'), { sensitivity: 'base' }));
    }
}

function resetFilters() {
    searchInput.value = '';
    filterRegion.value = 'all';
    populateSubregionFilters('all', 'all');
    sortSelect.value = 'name';
    applyFilters();
}

function buildSection(title, content, id = '') {
    return `
        <section class="detail-section" ${id ? `id="${id}"` : ''}>
            <h3>${escapeHTML(title)}</h3>
            ${content}
        </section>
    `;
}

function buildModalContent(country) {
    const coordinates = country.capitalCoords || country.latlng;
    const locationText = coordinates
        ? `${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(2)}`
        : t('noCoordinates');

    const density = country.area > 0 ? `${formatNumber((country.population / country.area).toFixed(2))} ${t('perKm2')}` : t('unknown');
    const mapSection = `<div id="countryMap"><div class="map-loader">${escapeHTML(t('loading'))}</div></div>`;

    const economyText = getFullSectionText(country, 'economy');
    const governmentText = getFullSectionText(country, 'government');
    const militaryText = getFullSectionText(country, 'military');
    const infrastructureText = getFullSectionText(country, 'infrastructure');
    const educationText = getFullSectionText(country, 'education');
    const healthText = getFullSectionText(country, 'health');
    const cultureText = getFullSectionText(country, 'culture');
    const securityText = getFullSectionText(country, 'security');
    const globalRoleText = getFullSectionText(country, 'globalRole');
    const bordersText = getBordersText(country);

    return `
        <div class="section-highlight">
            <div class="section-card section-card--highlight">
                <strong>${escapeHTML(t('flagSummary'))}</strong>
                <span>${escapeHTML(countryTitle(country))} (${escapeHTML(countryOfficial(country))})</span>
            </div>
            <div class="section-card section-card--highlight">
                <strong>${escapeHTML(t('capital'))}</strong>
                <span>${escapeHTML(localizeCapital(country.capital))}</span>
            </div>
        </div>

            <div class="section-group">
            ${buildSection(t('generalInfo'), `
                <p><strong>${escapeHTML(t('officialName'))}:</strong> ${escapeHTML(countryOfficial(country))}</p>
                <p><strong>${escapeHTML(t('capital'))}:</strong> ${escapeHTML(localizeCapital(country.capital))}</p>
                <p><strong>${escapeHTML(t('region'))}:</strong> ${escapeHTML(localizeRegion(country.region))}</p>
                <p><strong>${escapeHTML(t('subregion'))}:</strong> ${escapeHTML(localizeSubregion(country.subregion))}</p>
                <p><strong>${escapeHTML(t('independent'))}:</strong> ${escapeHTML(boolText(country.independent))}</p>
                <p><strong>${escapeHTML(t('unMember'))}:</strong> ${escapeHTML(boolText(country.unMember))}</p>
                <p><strong>${escapeHTML(t('tld'))}:</strong> ${escapeHTML(getTldText(country))}</p>
                <p><strong>${escapeHTML(t('callingCodes'))}:</strong> ${escapeHTML(getCallingCodesText(country))}</p>
                <p><strong>${escapeHTML(t('continents'))}:</strong> ${escapeHTML(localizeContinents(country.continents))}</p>
            `)}
            ${buildSection(t('geography'), `
                <p><strong>${escapeHTML(t('area'))}:</strong> ${formatNumber(country.area)} ${escapeHTML(t('km2'))}</p>
                <p><strong>${escapeHTML(t('landlocked'))}:</strong> ${escapeHTML(boolText(country.landlocked))}</p>
                <p><strong>${escapeHTML(t('coordinates'))}:</strong> ${escapeHTML(locationText)}</p>
                <p><strong>${escapeHTML(t('timezones'))}:</strong> ${escapeHTML(country.timezones)}</p>
                <p><strong>${escapeHTML(t('drivingSide'))}:</strong> ${escapeHTML(localizeDrivingSide(country.drivingSide))}</p>
                <p><strong>${escapeHTML(t('borders'))}:</strong> ${escapeHTML(bordersText)}</p>
                <div class="country-map-wrapper">
                    <h4>${escapeHTML(t('map'))}</h4>
                    ${mapSection}
                </div>
            `, 'geographySection')}
            ${buildSection(t('populationSection'), `
                <p><strong>${escapeHTML(t('population'))}:</strong> ${formatNumber(country.population)}</p>
                <p><strong>${escapeHTML(t('density'))}:</strong> ${escapeHTML(density)}</p>
                <p><strong>${escapeHTML(t('demonym'))}:</strong> ${escapeHTML(localizeDemonym(country.demonym))}</p>
                <p><strong>${escapeHTML(t('languages'))}:</strong> ${escapeHTML(localizeDelimitedText(country.languages))}</p>
                <p><strong>${escapeHTML(t('currencies'))}:</strong> ${escapeHTML(localizeDelimitedText(country.currencies))}</p>
            `, 'populationSection')}
            ${buildSection(t('economy'), `<p>${escapeHTML(economyText)}</p>`, 'economySection')}
            ${buildSection(t('government'), `<p>${escapeHTML(governmentText)}</p>`, 'governmentSection')}
            ${buildSection(t('military'), `<p>${escapeHTML(militaryText)}</p>`, 'militarySection')}
            ${buildSection(t('infrastructure'), `<p>${escapeHTML(infrastructureText)}</p>`, 'infrastructureSection')}
            ${buildSection(t('education'), `<p>${escapeHTML(educationText)}</p>`, 'educationSection')}
            ${buildSection(t('health'), `<p>${escapeHTML(healthText)}</p>`, 'healthSection')}
            ${buildSection(t('culture'), `<p>${escapeHTML(cultureText)}</p>`, 'cultureSection')}
            ${buildSection(t('security'), `<p>${escapeHTML(securityText)}</p>`, 'securitySection')}
            ${buildSection(t('globalRole'), `<p><strong>${escapeHTML(t('unMember'))}:</strong> ${escapeHTML(boolText(country.unMember))}</p><p>${escapeHTML(globalRoleText)}</p>`, 'globalRoleSection')}
        </div>
    `;
}

async function fetchCountryBoundary(country) {
    const cacheKey = country.cca3 || country.cca2 || country.raw?.name?.common;
    if (countryGeoJsonCache.has(cacheKey)) {
        return countryGeoJsonCache.get(cacheKey);
    }

    const urls = [
        `${COUNTRY_GEOJSON_BASE_URL}/${encodeURIComponent(country.cca3)}.geo.json`,
    ];
    const countryCode = country.cca2 ? country.cca2.toLowerCase() : '';
    const queryName = encodeURIComponent(country.raw?.name?.common || countryTitle(country));

    if (countryCode) {
        urls.push(`https://nominatim.openstreetmap.org/search?format=geojson&polygon_geojson=1&limit=1&countrycodes=${countryCode}&q=${queryName}`);
    }

    for (const url of urls) {
        try {
            const response = await fetch(url);
            if (!response.ok) continue;
            const data = await response.json();
            const geoJson = data.type === 'FeatureCollection' && data.features?.length ? data : null;
            if (geoJson) {
                countryGeoJsonCache.set(cacheKey, geoJson);
                return geoJson;
            }
        } catch (error) {
            console.warn('Country boundary failed:', error);
        }
    }

    countryGeoJsonCache.set(cacheKey, null);
    return null;
}

function hideMapLoader() {
    const loader = document.querySelector('#countryMap .map-loader');
    if (loader) loader.style.display = 'none';
}

function projectPoint(lon, lat) {
    const latitude = Math.max(Math.min(lat, 85), -85);
    const sin = Math.sin(latitude * Math.PI / 180);
    return [
        (lon + 180) / 360,
        0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI),
    ];
}

function collectGeoJsonRings(geometry, rings = []) {
    if (!geometry) return rings;

    if (geometry.type === 'Polygon') {
        geometry.coordinates.forEach(ring => rings.push(ring));
    } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach(polygon => polygon.forEach(ring => rings.push(ring)));
    } else if (geometry.type === 'GeometryCollection') {
        geometry.geometries.forEach(item => collectGeoJsonRings(item, rings));
    }

    return rings;
}

function getGeoJsonRings(geoJson) {
    if (!geoJson) return [];
    if (geoJson.type === 'FeatureCollection') {
        return geoJson.features.flatMap(feature => collectGeoJsonRings(feature.geometry));
    }
    if (geoJson.type === 'Feature') {
        return collectGeoJsonRings(geoJson.geometry);
    }
    return collectGeoJsonRings(geoJson);
}

function renderCountrySvgMap(country, geoJson) {
    const mapContainer = document.getElementById('countryMap');
    if (!mapContainer || !geoJson) return false;

    const rings = getGeoJsonRings(geoJson).filter(ring => ring.length > 2);
    if (!rings.length) return false;

    const projectedRings = rings.map(ring => ring.map(([lon, lat]) => projectPoint(lon, lat)));
    const points = projectedRings.flat();
    const minX = Math.min(...points.map(point => point[0]));
    const maxX = Math.max(...points.map(point => point[0]));
    const minY = Math.min(...points.map(point => point[1]));
    const maxY = Math.max(...points.map(point => point[1]));
    const width = 1000;
    const height = 420;
    const padding = 34;
    const spanX = maxX - minX || 1;
    const spanY = maxY - minY || 1;
    const scale = Math.min((width - padding * 2) / spanX, (height - padding * 2) / spanY);
    const offsetX = (width - spanX * scale) / 2;
    const offsetY = (height - spanY * scale) / 2;

    const pathData = projectedRings.map(ring => ring.map(([x, y], index) => {
        const sx = offsetX + (x - minX) * scale;
        const sy = offsetY + (y - minY) * scale;
        return `${index === 0 ? 'M' : 'L'}${sx.toFixed(2)} ${sy.toFixed(2)}`;
    }).join(' ') + ' Z').join(' ');

    mapContainer.innerHTML = `
        <div class="country-svg-map" role="img" aria-label="${escapeHTML(countryTitle(country))}">
            <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
                <defs>
                    <radialGradient id="countryGlow" cx="50%" cy="50%" r="65%">
                        <stop offset="0%" stop-color="#22c55e" stop-opacity="0.32" />
                        <stop offset="100%" stop-color="#22c55e" stop-opacity="0" />
                    </radialGradient>
                </defs>
                <rect width="${width}" height="${height}" fill="url(#countryGlow)" />
                <path d="${pathData}" />
            </svg>
            <div class="country-svg-caption">${escapeHTML(countryTitle(country))}</div>
        </div>
    `;
    return true;
}

function renderMapFallback(country) {
    const mapContainer = document.getElementById('countryMap');
    if (!mapContainer) return;
    const coordinates = country?.capitalCoords || country?.latlng || [];
    const marker = coordinates.length === 2 ? `${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(2)}` : t('unknown');

    mapContainer.innerHTML = `
        <div class="map-placeholder">
            <strong>${escapeHTML(countryTitle(country))}</strong>
            <span>${escapeHTML(t('coordinates'))}: ${escapeHTML(marker)}</span>
        </div>
    `;
}

function initMap(country) {
    const mapContainer = document.getElementById('countryMap');

    if (!mapContainer) return;
    if (detailMap) {
        detailMap.remove();
        detailMap = null;
    }

    mapContainer.innerHTML = `<div class="map-loader">${escapeHTML(t('loading'))}</div>`;
    activeCountryBoundary = null;

    fetchCountryBoundary(country).then(geoJson => {
        if (activeModalCountry?.cca3 !== country.cca3) return;
        if (!renderCountrySvgMap(country, geoJson)) {
            renderMapFallback(country);
        }
        hideMapLoader();
    }).catch(error => {
        console.warn('Map boundary render failed:', error);
        renderMapFallback(country);
        hideMapLoader();
    });
}

async function fetchWorldFactbook(country) {
    const slug = country.raw.name.common.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

    try {
        const response = await fetch(`https://worldfactbook.io/api/v1/countries/${slug}/`);
        if (!response.ok) throw new Error('No extra data');
        return await response.json();
    } catch (error) {
        return null;
    }
}

function updateFactbookSections(data) {
    const sectionMap = [
        ['economySection', 'economy', t('economy')],
        ['governmentSection', 'government', t('government')],
        ['militarySection', 'military', t('military')],
    ];

    sectionMap.forEach(([id, key, title]) => {
        const section = document.getElementById(id);
        if (section && data[key]) {
            section.innerHTML = `<h3>${escapeHTML(title)}</h3><p>${escapeHTML(data[key].text || t('pendingData'))}</p>`;
        }
    });
}

function openCountryModal(country) {
    activeModalCountry = country;
    modalTitle.textContent = countryTitle(country);
    modalSubtitle.textContent = `${localizeRegion(country.region)} · ${localizeSubregion(country.subregion)} · ${localizeCapital(country.capital)}`;
    modalBody.innerHTML = buildModalContent(country);
    modal.classList.add('show');
    initMap(country);
}

function closeCountryModal() {
    modal.classList.remove('show');
    activeModalCountry = null;
    if (detailMap) {
        detailMap.remove();
        detailMap = null;
    }
    activeCountryBoundary = null;
}

function bookText(book, field) {
    return book[field]?.[currentLanguage] || book[field]?.tg || book[field]?.en || '';
}

function renderBooks() {
    if (!booksList || !bookDetails) return;

    booksList.innerHTML = BOOKS.map(book => `
        <button class="book-card ${book.id === activeBookId ? 'active' : ''}" type="button" data-book-id="${escapeHTML(book.id)}">
            <span class="book-icon" aria-hidden="true">📘</span>
            <span>
                <span class="book-card-title">${escapeHTML(bookText(book, 'title'))}</span>
                <p>${escapeHTML(bookText(book, 'description'))}</p>
                <span class="book-meta">
                    <span>${escapeHTML(t('bookClass'))}: ${escapeHTML(book.grade)}</span>
                    <span>${escapeHTML(t('bookYear'))}: ${escapeHTML(book.year)}</span>
                    <span>${escapeHTML(t('bookSize'))}: ${escapeHTML(book.size)}</span>
                </span>
            </span>
        </button>
    `).join('');

    booksList.querySelectorAll('.book-card').forEach(card => {
        card.addEventListener('click', () => {
            activeBookId = card.dataset.bookId;
            renderBooks();
        });
    });

    const activeBook = BOOKS.find(book => book.id === activeBookId) || BOOKS[0];
    renderBookDetails(activeBook);
}

function renderBookDetails(book) {
    bookDetails.innerHTML = `
        <div class="book-detail-header">
            <div class="book-detail-icon" aria-hidden="true">📚</div>
            <h3>${escapeHTML(bookText(book, 'title'))}</h3>
            <p>${escapeHTML(bookText(book, 'description'))}</p>
        </div>
        <div class="book-meta">
            <span>${escapeHTML(t('bookClass'))}: ${escapeHTML(book.grade)}</span>
            <span>${escapeHTML(t('bookYear'))}: ${escapeHTML(book.year)}</span>
            <span>${escapeHTML(t('bookSize'))}: ${escapeHTML(book.size)}</span>
        </div>
        <div class="book-actions">
            <a class="book-action" href="${escapeHTML(book.path)}" target="_blank" rel="noopener">
                📖 ${escapeHTML(t('readBook'))}
            </a>
            <a class="book-action secondary" href="${escapeHTML(book.path)}" download="${escapeHTML(book.fileName)}">
                ⬇ ${escapeHTML(t('downloadBook'))}
            </a>
        </div>
    `;
}

function openBooksModal() {
    settingsPanel.classList.remove('open');
    settingsToggle.setAttribute('aria-expanded', 'false');
    renderBooks();
    booksModal.classList.add('show');
    booksToggle.setAttribute('aria-expanded', 'true');
}

function closeBooksModal() {
    booksModal.classList.remove('show');
    booksToggle.setAttribute('aria-expanded', 'false');
}

function quizText(item, field) {
    return item[field]?.[currentLanguage] || item[field]?.tg || item[field]?.en || '';
}

function formatQuizTime(ms) {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return `${minutes}:${seconds}`;
}

function getActiveQuizElapsed() {
    if (!quizSession || quizSession.complete) return 0;
    const player = quizSession.players[quizSession.activePlayerIndex];
    if (player?.complete) return player.elapsed;
    return Date.now() - quizSession.startTime;
}

function scoreQuizAnswers(answers) {
    const correct = QUIZ_QUESTIONS.reduce((sum, question, index) => {
        return sum + (answers[index] === question.answer ? 1 : 0);
    }, 0);
    const answered = answers.filter(answer => Number.isInteger(answer)).length;
    const wrong = answered - correct;

    return {
        score: correct * 10,
        correct,
        wrong,
    };
}

function stopQuizTimer() {
    if (quizTimerId) {
        clearInterval(quizTimerId);
        quizTimerId = null;
    }
}

function startQuizTimer() {
    stopQuizTimer();
    quizTimerId = setInterval(updateQuizTimerLabels, 500);
}

function updateQuizTimerLabels() {
    if (!quizSession) return;
    const activeTime = document.getElementById('quizActiveTime');
    if (activeTime && !quizSession.complete) {
        activeTime.textContent = formatQuizTime(getActiveQuizElapsed());
    }

    quizSession.players.forEach((player, index) => {
        const timeNode = document.getElementById(`quizPlayerTime-${index}`);
        if (timeNode) {
            const elapsed = player.complete ? player.elapsed : index === quizSession.activePlayerIndex ? getActiveQuizElapsed() : 0;
            timeNode.textContent = formatQuizTime(elapsed);
        }
    });
}

function setQuizMode(mode) {
    quizMode = mode === 'friend' ? 'friend' : 'self';
    quizModeButtons.forEach(button => {
        button.classList.toggle('active', button.dataset.quizMode === quizMode);
    });
    friendNameInput.disabled = quizMode !== 'friend';
    friendNameInput.classList.toggle('muted', quizMode !== 'friend');
}

function renderQuizAccess() {
    const isLoggedIn = Boolean(currentUser);
    quizLocked.classList.toggle('hidden', isLoggedIn);
    quizApp.classList.toggle('hidden', !isLoggedIn);

    if (!isLoggedIn) {
        stopQuizTimer();
        quizSession = null;
        quizStage.innerHTML = '';
        quizScoreboard.innerHTML = '';
        return;
    }

    setQuizMode(quizMode);
    if (quizSession) {
        renderQuiz();
    } else {
        renderQuizEmpty();
    }
}

function renderQuizEmpty() {
    stopQuizTimer();
    quizScoreboard.innerHTML = '';
    quizStage.innerHTML = `
        <div class="quiz-empty">
            <h3>${escapeHTML(t('quizEmptyTitle'))}</h3>
            <p>${escapeHTML(t('quizEmptyText'))}</p>
        </div>
    `;
}

function renderQuizScoreboard() {
    if (!quizSession) {
        quizScoreboard.innerHTML = '';
        return;
    }

    quizScoreboard.innerHTML = quizSession.players.map((player, index) => {
        const isActive = index === quizSession.activePlayerIndex && !quizSession.complete;
        const elapsed = player.complete ? player.elapsed : isActive ? getActiveQuizElapsed() : 0;
        return `
            <div class="quiz-score-card ${isActive ? 'active' : ''}">
                <strong>${escapeHTML(player.name)}</strong>
                <span>${escapeHTML(t('quizScore'))}: ${escapeHTML(player.score)}</span>
                <span>${escapeHTML(t('quizTime'))}: <span id="quizPlayerTime-${index}">${escapeHTML(formatQuizTime(elapsed))}</span></span>
                <span>${escapeHTML(t('quizTrue'))}: ${escapeHTML(player.correct)} / ${escapeHTML(t('quizFalse'))}: ${escapeHTML(player.wrong)}</span>
            </div>
        `;
    }).join('');
}

function startQuiz() {
    if (!currentUser) {
        showAlert(t('quizLoginPrompt'), 'error', 4000);
        renderQuizAccess();
        return;
    }

    const friendName = friendNameInput.value.trim() || t('quizFriendMode');
    const players = quizMode === 'friend'
        ? [currentUser.name || currentUser.email, friendName]
        : [currentUser.name || currentUser.email];

    quizSession = {
        players: players.map(name => ({
            name,
            answers: Array(QUIZ_QUESTIONS.length).fill(null),
            score: 0,
            correct: 0,
            wrong: 0,
            elapsed: 0,
            complete: false,
        })),
        activePlayerIndex: 0,
        currentQuestionIndex: 0,
        startTime: Date.now(),
        complete: false,
    };

    startQuizTimer();
    renderQuiz();
}

function resetQuiz() {
    quizSession = null;
    renderQuizEmpty();
}

function renderQuiz() {
    if (!quizSession) {
        renderQuizEmpty();
        return;
    }

    renderQuizScoreboard();

    if (quizSession.complete) {
        renderQuizResult();
        return;
    }

    renderQuizQuestion();
    updateQuizTimerLabels();
}

function renderQuizQuestion() {
    const question = QUIZ_QUESTIONS[quizSession.currentQuestionIndex];
    const player = quizSession.players[quizSession.activePlayerIndex];
    const selectedAnswer = player.answers[quizSession.currentQuestionIndex];
    const hasAnswer = Number.isInteger(selectedAnswer);
    const isLastQuestion = quizSession.currentQuestionIndex === QUIZ_QUESTIONS.length - 1;

    quizStage.innerHTML = `
        <div class="quiz-progress">
            <span>${escapeHTML(t('quizPlayerTurn'))}: ${escapeHTML(player.name)}</span>
            <span>${escapeHTML(t('quizQuestion'))} ${quizSession.currentQuestionIndex + 1}/${QUIZ_QUESTIONS.length}</span>
            <span>${escapeHTML(t('quizTime'))}: <strong id="quizActiveTime">${escapeHTML(formatQuizTime(getActiveQuizElapsed()))}</strong></span>
        </div>
        <div class="quiz-question">
            <h3>${escapeHTML(quizText(question, 'question'))}</h3>
            <div class="quiz-options">
                ${question.options[currentLanguage]?.map((option, index) => {
                    const isSelected = selectedAnswer === index;
                    const isCorrect = question.answer === index;
                    const stateClass = hasAnswer && isCorrect ? 'correct' : hasAnswer && isSelected ? 'wrong' : '';
                    return `
                        <button class="quiz-option ${isSelected ? 'selected' : ''} ${stateClass}" type="button" data-answer-index="${index}" ${hasAnswer ? 'disabled' : ''}>
                            <span>${String.fromCharCode(65 + index)}</span>
                            ${escapeHTML(option)}
                        </button>
                    `;
                }).join('') || ''}
            </div>
        </div>
        ${hasAnswer ? `
            <div class="quiz-feedback ${selectedAnswer === question.answer ? 'correct' : 'wrong'}">
                <strong>${selectedAnswer === question.answer ? escapeHTML(t('quizTrue')) : escapeHTML(t('quizFalse'))}</strong>
                <span>${escapeHTML(t('quizCorrectAnswer'))}: ${escapeHTML(question.options[currentLanguage]?.[question.answer] || '')}</span>
            </div>
            <button id="quizNextBtn" class="button-primary" type="button">
                ${escapeHTML(isLastQuestion ? t('finishQuiz') : t('nextQuestion'))}
            </button>
        ` : ''}
    `;
}

function answerQuizQuestion(answerIndex) {
    if (!quizSession || quizSession.complete) return;
    const player = quizSession.players[quizSession.activePlayerIndex];
    if (Number.isInteger(player.answers[quizSession.currentQuestionIndex])) return;

    player.answers[quizSession.currentQuestionIndex] = answerIndex;
    renderQuiz();
}

function goToNextQuizQuestion() {
    if (!quizSession) return;

    if (quizSession.currentQuestionIndex < QUIZ_QUESTIONS.length - 1) {
        quizSession.currentQuestionIndex += 1;
        renderQuiz();
        return;
    }

    finishActiveQuizPlayer();
}

function finishActiveQuizPlayer() {
    const player = quizSession.players[quizSession.activePlayerIndex];
    const result = scoreQuizAnswers(player.answers);
    player.score = result.score;
    player.correct = result.correct;
    player.wrong = result.wrong;
    player.elapsed = Date.now() - quizSession.startTime;
    player.complete = true;

    if (quizSession.activePlayerIndex < quizSession.players.length - 1) {
        quizSession.activePlayerIndex += 1;
        quizSession.currentQuestionIndex = 0;
        quizSession.startTime = Date.now();
        renderFriendTurn();
        return;
    }

    quizSession.complete = true;
    stopQuizTimer();
    renderQuiz();
}

function renderFriendTurn() {
    renderQuizScoreboard();
    const player = quizSession.players[quizSession.activePlayerIndex];
    quizStage.innerHTML = `
        <div class="quiz-empty">
            <h3>${escapeHTML(t('quizFriendReady'))}</h3>
            <p>${escapeHTML(t('quizPlayerTurn'))}: ${escapeHTML(player.name)}</p>
            <button id="continueFriendQuizBtn" class="button-primary" type="button">${escapeHTML(t('startQuiz'))}</button>
        </div>
    `;
}

function renderQuizResult() {
    renderQuizScoreboard();
    const bestScore = Math.max(...quizSession.players.map(player => player.score));
    const winners = quizSession.players.filter(player => player.score === bestScore);
    const resultTitle = winners.length > 1 ? t('quizDraw') : `${t('quizWinner')}: ${winners[0].name}`;

    quizStage.innerHTML = `
        <div class="quiz-result">
            <h3>${escapeHTML(t('quizResult'))}</h3>
            <p class="quiz-winner">${escapeHTML(resultTitle)}</p>
            <div class="quiz-review">
                ${quizSession.players.map(player => `
                    <div class="quiz-review-player">
                        <h4>${escapeHTML(player.name)}</h4>
                        ${QUIZ_QUESTIONS.map((question, index) => {
                            const answerIndex = player.answers[index];
                            const answerText = Number.isInteger(answerIndex)
                                ? question.options[currentLanguage]?.[answerIndex]
                                : t('quizNoAnswer');
                            const correctText = question.options[currentLanguage]?.[question.answer] || '';
                            return `
                                <div class="quiz-review-row ${answerIndex === question.answer ? 'correct' : 'wrong'}">
                                    <strong>${index + 1}. ${escapeHTML(quizText(question, 'question'))}</strong>
                                    <span>${escapeHTML(t('quizYourAnswer'))}: ${escapeHTML(answerText)}</span>
                                    <span>${escapeHTML(t('quizCorrectAnswer'))}: ${escapeHTML(correctText)}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function openQuizModal() {
    settingsPanel.classList.remove('open');
    settingsToggle.setAttribute('aria-expanded', 'false');
    renderQuizAccess();
    quizModal.classList.add('show');
    quizToggle.setAttribute('aria-expanded', 'true');
}

function closeQuizModal() {
    quizModal.classList.remove('show');
    quizToggle.setAttribute('aria-expanded', 'false');
}

function loadStoredUser() {
    try {
        return JSON.parse(localStorage.getItem('currentUser')) || null;
    } catch (error) {
        return null;
    }
}

function saveCurrentUser(user) {
    currentUser = user;
    if (user) {
        localStorage.setItem('currentUser', JSON.stringify(user));
    } else {
        localStorage.removeItem('currentUser');
    }
    updateAuthUI();
}

function showAuthMessage(message, type = 'success') {
    authMessage.textContent = message;
    authMessage.className = `auth-message ${type === 'error' ? 'error' : ''}`;
    authMessage.classList.remove('hidden');
}

function clearAuthMessage() {
    authMessage.textContent = '';
    authMessage.className = 'auth-message hidden';
}

async function sendAuthRequest(path, payload) {
    const response = await fetch(`${AUTH_API_BASE}${path}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || t('authServerError'));
    }

    return data;
}

function updateAuthUI() {
    if (!authToggleText || !authLoggedOut || !authLoggedIn) return;

    const isLoggedIn = Boolean(currentUser);
    authToggleIcon.textContent = isLoggedIn ? '✅' : '👤';
    authToggleText.textContent = isLoggedIn ? t('authButtonLoggedIn') : t('authButton');
    authStatusBadge.textContent = isLoggedIn ? t('authBadgeLoggedIn') : t('authBadge');
    authLoggedOut.classList.toggle('hidden', isLoggedIn);
    authLoggedIn.classList.toggle('hidden', !isLoggedIn);

    if (isLoggedIn) {
        authUserName.textContent = currentUser.name;
        authUserEmail.textContent = currentUser.email;
    }

    if (quizModal?.classList.contains('show')) {
        renderQuizAccess();
    }
}

function openAuthModal() {
    clearAuthMessage();
    updateAuthUI();
    authModal.classList.add('show');
    authToggle.setAttribute('aria-expanded', 'true');
}

function closeAuthModal() {
    authModal.classList.remove('show');
    authToggle.setAttribute('aria-expanded', 'false');
}

async function handleLogin(event) {
    event.preventDefault();
    clearAuthMessage();

    const formData = new FormData(loginForm);
    try {
        const data = await sendAuthRequest('/api/login', {
            email: formData.get('email'),
            password: formData.get('password'),
        });
        saveCurrentUser(data.user);
        loginForm.reset();
        showAuthMessage(t('loginSuccess'));
    } catch (error) {
        showAuthMessage(error.message || t('authServerError'), 'error');
    }
}

async function handleRegister(event) {
    event.preventDefault();
    clearAuthMessage();

    const formData = new FormData(registerForm);
    try {
        const data = await sendAuthRequest('/api/register', {
            name: formData.get('name'),
            email: formData.get('email'),
            password: formData.get('password'),
        });
        saveCurrentUser(data.user);
        registerForm.reset();
        showAuthMessage(t('registerSuccess'));
    } catch (error) {
        showAuthMessage(error.message || t('authServerError'), 'error');
    }
}

function handleLogout() {
    saveCurrentUser(null);
    showAuthMessage(t('logoutSuccess'));
}

function applyTheme(theme) {
    currentTheme = theme === 'light' ? 'light' : 'dark';
    document.body.classList.toggle('light-theme', currentTheme === 'light');
    localStorage.setItem('siteTheme', currentTheme);

    themeButtons.forEach(button => {
        button.classList.toggle('active', button.dataset.themeOption === currentTheme);
    });
}

function applyLanguage(language) {
    currentLanguage = TRANSLATIONS[language] ? language : 'tg';
    document.documentElement.lang = currentLanguage;
    document.title = t('heroTitle');
    languageSelect.value = currentLanguage;
    localStorage.setItem('siteLanguage', currentLanguage);

    document.querySelectorAll('[data-i18n]').forEach(element => {
        element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        element.placeholder = t(element.dataset.i18nPlaceholder);
    });
    document.querySelectorAll('[data-i18n-aria-label]').forEach(element => {
        element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel));
    });

    if (allCountries.length) {
        const selectedRegion = filterRegion.value || 'all';
        const selectedSubregion = filterSubregion.value || 'all';
        populateRegionFilters(selectedRegion);
        populateSubregionFilters(filterRegion.value, selectedSubregion);
        applyFilters();
    }

    renderBooks();
    if (quizModal?.classList.contains('show')) {
        renderQuizAccess();
    }
    updateAuthUI();

    if (activeModalCountry) openCountryModal(activeModalCountry);
}

function registerEvents() {
    settingsToggle.addEventListener('click', () => {
        settingsPanel.classList.toggle('open');
        settingsToggle.setAttribute('aria-expanded', settingsPanel.classList.contains('open').toString());
    });

    booksToggle.addEventListener('click', openBooksModal);
    quizToggle.addEventListener('click', openQuizModal);
    authToggle.addEventListener('click', openAuthModal);

    document.addEventListener('click', event => {
        if (!settingsPanel.contains(event.target)) {
            settingsPanel.classList.remove('open');
            settingsToggle.setAttribute('aria-expanded', 'false');
        }
    });

    themeButtons.forEach(button => {
        button.addEventListener('click', () => applyTheme(button.dataset.themeOption));
    });

    languageSelect.addEventListener('change', () => applyLanguage(languageSelect.value));
    searchInput.addEventListener('input', applyFilters);
    filterRegion.addEventListener('change', () => {
        populateSubregionFilters(filterRegion.value, 'all');
        applyFilters();
    });
    filterSubregion.addEventListener('change', applyFilters);
    sortSelect.addEventListener('change', () => {
        applySort();
        renderCountries(activeCountries);
    });
    resetBtn.addEventListener('click', resetFilters);

    closeModalButton.addEventListener('click', closeCountryModal);
    modal.addEventListener('click', event => {
        if (event.target === modal) closeCountryModal();
    });
    closeBooksModalButton.addEventListener('click', closeBooksModal);
    booksModal.addEventListener('click', event => {
        if (event.target === booksModal) closeBooksModal();
    });
    closeQuizModalButton.addEventListener('click', closeQuizModal);
    quizModal.addEventListener('click', event => {
        if (event.target === quizModal) closeQuizModal();
    });
    quizLoginBtn.addEventListener('click', () => {
        closeQuizModal();
        openAuthModal();
    });
    quizModeButtons.forEach(button => {
        button.addEventListener('click', () => {
            setQuizMode(button.dataset.quizMode);
            resetQuiz();
        });
    });
    startQuizBtn.addEventListener('click', startQuiz);
    resetQuizBtn.addEventListener('click', resetQuiz);
    quizStage.addEventListener('click', event => {
        const option = event.target.closest('[data-answer-index]');
        if (option) {
            answerQuizQuestion(Number(option.dataset.answerIndex));
            return;
        }
        if (event.target.closest('#quizNextBtn')) {
            goToNextQuizQuestion();
            return;
        }
        if (event.target.closest('#continueFriendQuizBtn')) {
            startQuizTimer();
            renderQuiz();
        }
    });
    closeAuthModalButton.addEventListener('click', closeAuthModal);
    authModal.addEventListener('click', event => {
        if (event.target === authModal) closeAuthModal();
    });
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    logoutBtn.addEventListener('click', handleLogout);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            if (modal.classList.contains('show')) closeCountryModal();
            if (booksModal.classList.contains('show')) closeBooksModal();
            if (quizModal.classList.contains('show')) closeQuizModal();
            if (authModal.classList.contains('show')) closeAuthModal();
            settingsPanel.classList.remove('open');
            settingsToggle.setAttribute('aria-expanded', 'false');
        }
    });
}

async function loadCountries() {
    const sources = [LOCAL_COUNTRIES_URL, fetchRemoteCountries, API_URL];

    try {
        showAlert(t('loading'), 'info', 0);
        await loadCountryNameTranslations();

        let data = null;
        let lastError = null;

        for (const source of sources) {
            try {
                let result = null;

                if (typeof source === 'function') {
                    result = await source();
                } else {
                    const response = await fetch(source);
                    if (!response.ok) throw new Error(`${source}: HTTP ${response.status}`);
                    result = await response.json();
                }

                if (!Array.isArray(result) || result.length === 0) {
                    throw new Error(`${source}: empty country list`);
                }

                data = result;
                break;
            } catch (error) {
                lastError = error;
                console.warn('Country source failed:', error);
            }
        }

        if (!data) throw lastError || new Error('No country data');

        allCountries = data.map(normalizeCountry);
        activeCountries = [...allCountries];
        populateRegionFilters();
        applySort();
        renderCountries(activeCountries);
        showAlert(t('loaded'), 'success', 4000);
    } catch (error) {
        showAlert(t('loadError'), 'error', 0);
        resultsGrid.innerHTML = `<div class="empty-state">${escapeHTML(t('loadErrorState'))}</div>`;
        console.error('API Error:', error);
    }
}

applyTheme(currentTheme);
applyLanguage(currentLanguage);
registerEvents();
loadCountries();
