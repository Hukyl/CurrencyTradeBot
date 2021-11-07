import datetime as dt

from .decorators import rangetest


@rangetest(strict_range=False, utcoffset=(-11, 12))
def adapt_datetime(d: dt.datetime, utcoffset: int = 0):
    assert d.tzinfo is None, "can not add utcoffset to non-UTC datetime"
    return d.replace(
        day=d.day + ((d.hour + utcoffset) // 24),
        hour=(d.hour + utcoffset) % 24,
        microsecond=0,
        tzinfo=dt.timezone(dt.timedelta(0, utcoffset*60*60)) 
    )


@rangetest(strict_range=False, utcoffset=(-11, 12))
def convert_datetime(d: dt.datetime, utcoffset: int = 0):
    assert d.tzinfo is None, "can not remove utcoffset to non-UTC datetime"
    if d.hour - utcoffset < 0:
        d = d.replace(day=d.day - 1, hour=d.hour + 24 - utcoffset)
    else:
        d = d.replace(hour=d.hour - utcoffset)
    return d.replace(microsecond=0, tzinfo=None)


def get_now():
    return dt.datetime.utcnow().replace(microsecond=0)


def check_datetime_in_future(up_to_date: dt.datetime):
    assert up_to_date.tzinfo is None, \
           'can compare only timezone-naive datetime'
    now = get_now() 
    return up_to_date >= now


@rangetest(strict_range=False, utcoffset=(-11, 12))
def convert_check_times(check_times: list, utcoffset: int = 0):
    return [
        (
            dt.datetime.strptime(t, '%H:%M') - dt.timedelta(hours=utcoffset)
        ).strftime('%H:%M')
        for t in check_times
    ]


@rangetest(strict_range=False, utcoffset=(-11, 12))
def adapt_check_times(check_times: list, utcoffset: int = 0):
    return [
        (
            dt.datetime.strptime(t, '%H:%M') + dt.timedelta(hours=utcoffset)
        ).strftime('%H:%M')
        for t in check_times
    ]


def convert_from_country_format(datetime_str: str, country: str):
    if country == 'ru':
        check_str = '%d.%m.%Y %H:%M'
    elif country == 'en':
        check_str = '%m-%d-%Y %I:%M %p'
    else:
        check_str = '%Y-%m-%d %H:%M'
    return dt.datetime.strptime(datetime_str, check_str)


def convert_to_country_format(d: dt.datetime, country: str):
    countries_formats = {
        'ru': '%d.%m.%Y %H:%M',
        'en': '%m-%d-%Y %I:%M %p'
    }
    return d.strftime(countries_formats.get(country, '%Y-%m-%d %H:%M'))


def get_country_dt_example(language: str = 'en'):
    examples = {
        'ru': 'ДД.ММ.ГГГГ ЧЧ:ММ',
        'en': 'MM-DD-YYYY HH:МI AM/PM',
        'default': 'YYYY-MM-DD HH:MI'
    }
    return examples.get(language, examples['default'])
