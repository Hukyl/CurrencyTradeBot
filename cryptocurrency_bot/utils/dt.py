import datetime as dt
from . import prettify_utcoffset



def add_offset(d:dt.datetime, utcoffset:int=0):
    """
    Adds tzinfo to `d` according to `utcoffset` offset
    """
    return d.replace(
            tzinfo=dt.timezone(dt.timedelta(0, utcoffset*60*60)) 
        )


def get_current_datetime(utcoffset:int=0):
    assert utcoffset in range(-11, 13), 'time zones are in range from -11 to +12'
    n = dt.datetime.utcnow()
    n = n.replace(
        day=n.day + ((n.hour + utcoffset) // 24),
        hour=(n.hour + utcoffset) % 24,
        microsecond=0
    )
    return add_offset(n, utcoffset)


def check_datetime_in_future(up_to_date:dt.datetime, utcoffset:int=0):
    assert up_to_date.tzinfo is not None, 'can compare only timezone-aware datetime'
    assert utcoffset in range(-11, 13), 'time zones are in range from -11 to +12'
    now = get_current_datetime(utcoffset=utcoffset) 
    return (now - up_to_date).total_seconds() <= 0


def convert_from_country_format(datetime_str:str, country:str, utcoffset:int=0):
    assert utcoffset in range(-11, 13), 'time zones are in range from -11 to +12'
    if country == 'ru':
        check_str = '%d.%m.%Y %H:%M'
    elif country == 'en':
        check_str = '%m-%d-%Y %I:%M %p'
    else:
        check_str = '%Y-%m-%d %H:%M'
    d = dt.datetime.strptime(datetime_str, check_str)
    return add_offset(d, utcoffset)


def convert_to_country_format(d:dt.datetime, country:str, no_offset:bool=False):
    if country == 'ru':
        format_str = '%d.%m.%Y %H:%M'
    elif country == 'en':
        format_str = '%m-%d-%Y %I:%M %p'
    else:
        format_str = '%Y-%m-%d %H:%M'
    if d.tzinfo and (not no_offset):
        format_str += f" UTC{str(d)[-6:]}"
    return d.strftime(format_str)