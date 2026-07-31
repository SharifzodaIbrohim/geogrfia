#!/usr/bin/env python3
import json
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTRIES_FULL_FILE = ROOT / 'data' / 'countries-full.json'
API_URL = 'https://restcountries.com/v3.1/all'
FIELDS_BATCHES = [
    'cca3,name,capital,region,subregion,population,area,landlocked,independent,tld',
    'cca3,idd,currencies,languages,borders,timezones,demonyms,unMember',
]

REGION_TRANSLATIONS = {
    'tg': {
        'Africa': 'Африқо',
        'Americas': 'Амрико',
        'Antarctic': 'Антарктида',
        'Antarctica': 'Антарктида',
        'Asia': 'Осиё',
        'Europe': 'Аврупо',
        'Oceania': 'Уқёнусия',
    },
    'ru': {
        'Africa': 'Африка',
        'Americas': 'Америка',
        'Antarctic': 'Антарктика',
        'Antarctica': 'Антарктика',
        'Asia': 'Азия',
        'Europe': 'Европа',
        'Oceania': 'Океания',
    },
}

LANGUAGE_TEMPLATES = {
    'economy': {
        'tg': '{name}-ро аҳолии {population} нафар ва майдони {area} км² муайян мекунад. Иқтисодиёт бештар ба {sector} ва истифодаи асъори {currencies} такя мекунад.',
        'ru': '{name} характеризуется населением {population} и площадью {area} км². Экономика опирается главным образом на {sector} и валюту {currencies}.',
        'en': '{name} has a population of {population} and an area of {area} km². Its economy mainly depends on {sector} and uses the currency {currencies}.',
    },
    'government': {
        'tg': '{name} {status_phrase} дар минтақаи {region} аст. Пойтахташ {capital} мебошад ва он {independent_phrase} ва {un_phrase}.',
        'ru': '{name} {status_phrase} в регионе {region}. Столица — {capital}, и страна {independent_phrase} и {un_phrase}.',
        'en': '{name} {status_phrase} in the {region} region. Its capital is {capital}, and the country {independent_phrase} and {un_phrase}.',
    },
    'military': {
        'tg': 'Ҳифзи {name} тавассути қувваҳои мусаллаҳ ва назорати марзҳо таъмин мешавад. Он {border_phrase} дорад ва дар самти амният диққат медиҳад.',
        'ru': 'Оборона {name} обеспечивается вооружёнными силами и контролем границ. Страна имеет {border_phrase} и уделяет внимание безопасности.',
        'en': '{name} protects itself through armed forces and border control. It has {border_phrase} and focuses on security.',
    },
    'infrastructure': {
        'tg': 'Инфрасохтори {name} аз пойтахт {capital}, роҳҳо, алоқа ва зонҳои вақтӣ иборат аст. Система барои рушди молия ва савдо муҳим аст.',
        'ru': 'Инфраструктура {name} включает столицу {capital}, дороги, связь и часовые пояса. Система важна для экономики и торговли.',
        'en': '{name} has infrastructure centered on its capital {capital}, transport, communication, and time zones. The system is important for commerce and daily life.',
    },
    'education': {
        'tg': 'Таълими дар {name} асосан дар мактабҳои ибтидоӣ, миёна ва олӣ бо марказҳо дар {capital} амал мекунад.',
        'ru': 'Образование в {name} основано на начальных, средних и высших школах, с важными центрами в {capital}.',
        'en': 'Education in {name} is organized through primary, secondary, and higher institutions, with major centers in {capital}.',
    },
    'health': {
        'tg': 'Система тандурустӣ дар {name} хидматрасониҳои асосиро пешкаш мекунад, махсусан дар пойтахт {capital}.',
        'ru': 'Здравоохранение в {name} предоставляет основные услуги, особенно в столице {capital}.',
        'en': 'Healthcare in {name} provides core services, especially in the capital {capital}.',
    },
    'culture': {
        'tg': 'Фарҳанги {name} ба забонҳои {languages} ва номҳои шаҳрвандӣ {demonym} асос ёфтааст. Мероси миллӣ муҳим аст.',
        'ru': 'Культура {name} опирается на языки {languages} и жителей, называемых {demonym}. Национальное наследие важно.',
        'en': 'The culture of {name} is shaped by languages {languages} and people known as {demonym}. Its national heritage is important.',
    },
    'security': {
        'tg': 'Дар {name}, амният тавассути назорати {border_phrase}, қонунгузорӣ ва ҳифзи шаҳрвандон нигоҳ дошта мешавад.',
        'ru': 'В {name} безопасность поддерживается контролем {border_phrase}, законодательством и защитой граждан.',
        'en': 'In {name}, security is maintained through control of {border_phrase}, law, and citizen protection.',
    },
    'globalRole': {
        'tg': '{name} ҳамчун узви СММ ва қисми минтақаи {region} дар муносибатҳои байналмилалӣ иштирок мекунад.',
        'ru': '{name} как член ООН и часть региона {region} участвует в международных отношениях.',
        'en': '{name} participates in international relations as a UN member and part of the {region} region.',
    },
    'independence': {
        'tg': '{name} {independent_phrase}.',
        'ru': '{name} {independent_phrase}.',
        'en': '{name} {independent_phrase}.',
    },
}

SECTOR_TEMPLATES = {
    'landlocked': {
        'tg': 'кишоварзӣ, тиҷорат ва хизматрасониҳои маҳаллӣ',
        'ru': 'сельское хозяйство, торговлю и местные услуги',
        'en': 'agriculture, trade, and local services',
    },
    'island': {
        'tg': 'туризм, чарогоҳҳо ва савдо',
        'ru': 'туризм, рыболовство и торговлю',
        'en': 'tourism, fishing, and trade',
    },
    'general': {
        'tg': 'савдо, хизматрасонӣ ва истеҳсолот',
        'ru': 'торговлю, услуги и производство',
        'en': 'trade, services, and manufacturing',
    },
}

session = requests.Session()
session.headers.update({'User-Agent': 'geogrfia-full-data-generator/1.0'})


def read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_join(items):
    items = [item for item in items if item]
    return ', '.join(items) if items else '—'


def format_population(value):
    return f'{int(value):,}'.replace(',', ' ')


def format_area(value):
    return f'{int(value):,}'.replace(',', ' ')


def choice_sector(country):
    if country.get('landlocked'):
        return SECTOR_TEMPLATES['landlocked']
    if country.get('region') == 'Oceania' or country.get('subregion') in ('Caribbean', 'Polynesia', 'Micronesia', 'Melanesia'):
        return SECTOR_TEMPLATES['island']
    return SECTOR_TEMPLATES['general']


def region_label(region, lang):
    return REGION_TRANSLATIONS.get(lang, {}).get(region, region)


def tld_text(tld_list):
    if not tld_list:
        return '—'
    return ', '.join(tld_list)


def calling_code_text(idd):
    if not idd or not idd.get('root'):
        return '—'
    suffixes = idd.get('suffixes') or []
    return ', '.join(f"{idd['root']}{suffix}" for suffix in suffixes)


def languages_text(langs):
    if not langs:
        return '—'
    return ', '.join(langs.values())


def currencies_text(currencies):
    if not currencies:
        return '—'
    pairs = []
    for currency in currencies.values():
        name = currency.get('name')
        symbol = currency.get('symbol')
        pairs.append(f"{name} ({symbol})" if symbol else name)
    return ', '.join(pairs)


def demonym_text(demonyms):
    if not demonyms:
        return '—'
    eng = demonyms.get('eng') or {}
    return eng.get('m') or eng.get('f') or '—'


def status_phrase(country, lang):
    independent = country.get('independent')
    if independent is True:
        return {
            'tg': 'соҳибихтиёр аст',
            'ru': 'является независимой',
            'en': 'is independent',
        }[lang]
    return {
        'tg': 'соҳибихтиёр нест',
        'ru': 'не является независимой',
        'en': 'is not independent',
    }[lang]


def status_phrase(country, lang):
    independent = country.get('independent')
    if independent is True:
        return {
            'tg': 'як давлати соҳибихтиёр аст',
            'ru': 'является суверенным независимым государством',
            'en': 'is a sovereign independent country',
        }[lang]
    return {
        'tg': 'мақоми махсуси маъмурӣ ё минтақа аст',
        'ru': 'имеет специальный административный статус',
        'en': 'is a territory or special administrative region',
    }[lang]


def independent_phrase(country, lang):
    if country.get('independent') is True:
        return {
            'tg': 'соҳибихтиёр аст',
            'ru': 'является независимой',
            'en': 'is independent',
        }[lang]
    return {
        'tg': 'соҳибихтиёр нест',
        'ru': 'не является независимой',
        'en': 'is not independent',
    }[lang]


def un_phrase(country, lang):
    if country.get('unMember'):
        return {
            'tg': 'узви СММ аст',
            'ru': 'является членом ООН',
            'en': 'is a UN member',
        }[lang]
    return {
        'tg': 'узви СММ нест',
        'ru': 'не является членом ООН',
        'en': 'is not a UN member',
    }[lang]


def border_phrase(country, lang):
    borders = country.get('borders') or []
    if not borders:
        return {
            'tg': 'бе марзҳои заминӣ',
            'ru': 'без сухопутных границ',
            'en': 'no land borders',
        }[lang]
    count = len(borders)
    return {
        'tg': f'марзҳои заминӣ бо {count} ҳамсоя',
        'ru': f'сухопутные границы с {count} соседями',
        'en': f'land borders with {count} neighbors',
    }[lang]


def build_section_text(country, section, lang):
    common = {
        'name': country.get('name'),
        'population': format_population(country.get('population') or 0),
        'area': format_area(country.get('area') or 0),
        'currencies': currencies_text(country.get('currencies')),
        'capital': safe_join(country.get('capital') or []),
        'region': region_label(country.get('region') or '—', lang),
        'languages': languages_text(country.get('languages')),
        'demonym': demonym_text(country.get('demonyms')),
        'border_phrase': border_phrase(country, lang),
        'status_phrase': status_phrase(country, lang),
        'independent_phrase': independent_phrase(country, lang),
        'un_phrase': un_phrase(country, lang),
    }
    if section == 'economy':
        common['sector'] = choice_sector(country)[lang]
    return LANGUAGE_TEMPLATES[section][lang].format(**common)


def fetch_rest_countries():
    print('Fetching full country data from REST Countries API...')
    countries = {}
    for batch in FIELDS_BATCHES:
        response = session.get(API_URL, params={'fields': batch}, timeout=30)
        response.raise_for_status()
        for country in response.json():
            cca3 = country.get('cca3')
            if not cca3:
                continue
            if cca3 not in countries:
                countries[cca3] = {}
            countries[cca3].update(country)
    return list(countries.values())


def normalize_country(country):
    return {
        'name': country.get('name', {}).get('common') or country.get('cca3'),
        'officialName': country.get('name', {}).get('official'),
        'capital': country.get('capital') or [],
        'region': country.get('region'),
        'subregion': country.get('subregion'),
        'population': country.get('population'),
        'area': country.get('area'),
        'landlocked': country.get('landlocked'),
        'unMember': country.get('unMember'),
        'independent': country.get('independent'),
        'tld': country.get('tld'),
        'idd': country.get('idd'),
        'currencies': country.get('currencies'),
        'languages': country.get('languages'),
        'borders': country.get('borders'),
        'timezones': country.get('timezones'),
        'demonyms': country.get('demonyms'),
        'status': country.get('status'),
    }


def main():
    countries_raw = fetch_rest_countries()
    full_data = {}
    for idx, country in enumerate(sorted(countries_raw, key=lambda c: c.get('cca3') or ''), 1):
        cca3 = country.get('cca3')
        if not cca3:
            continue
        normalized = normalize_country(country)
        item = {}
        for section in LANGUAGE_TEMPLATES.keys():
            item[section] = {
                'tg': build_section_text(normalized, section, 'tg'),
                'ru': build_section_text(normalized, section, 'ru'),
                'en': build_section_text(normalized, section, 'en'),
            }
        full_data[cca3] = item
        if idx % 50 == 0:
            print(f'Generated {idx}/{len(countries_raw)} countries')
    write_json(COUNTRIES_FULL_FILE, full_data)
    print(f'Done. Wrote {len(full_data)} entries to {COUNTRIES_FULL_FILE}')


if __name__ == '__main__':
    main()
