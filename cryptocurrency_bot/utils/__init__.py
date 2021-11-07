import json
import os

from proxy import Proxy

from configs import settings
from . import decorators, agent, dt, telegram, translator


proxy_fetcher = Proxy()

__all__ = [
    'merge_dicts', 'prettify_utcoffset', 'get_json_config', 
    'substract_percent', 'get_default_rates', 'prettify_float',
    'prettify_percent', 'get_proxy_list', 'decorators',
    'agent', 'dt', 'telegram', 'translator'
]


def merge_dicts(*dicts):
    assert len(dicts) > 0, 'you must pass minimum one dictionary'
    start_dct = dicts[0]
    for dct in dicts[1:]:
        start_dct = {**start_dct, **dct}
    return start_dct


@decorators.rangetest(strict_range=False, utcoffset=(-11, 12))
def prettify_utcoffset(utcoffset: int = 0):
    return "UTC" + ('' if utcoffset == 0 else '{:0=+3d}:00'.format(utcoffset))


def get_json_config():
    with open(
            os.path.join('configs', 'config.json'), 'r', 
            encoding='utf-8'
            ) as f:
        return json.load(f)


def get_proxy_list():
    return [':'.join(x[:2]) for x in proxy_fetcher.fetch_proxies()]


def get_default_rates(*args, to_print: bool = True):
    if len(args) == 0:
        return None
    if to_print:
        print('[ERROR] Default value was used for: ' + ', '.join(args))
    json_config = get_json_config()
    return {curr: json_config.get('initialValue' + curr, 1) for curr in args}


def prettify_float(num: float):
    round_num = settings.PRECISION_NUMBER + (0 if num // 1 > 0 else 3)
    return int(num) if num % 1 == 0 else round(num, round_num)


def prettify_percent(n: float, to_sign: bool = False):
    res = n * 100
    res = round(
        res, 
        settings.PERCENT_PRECISION_NUMBER if res > 1 else 6
    )  # bigger precision for float numbers between 0 and 1
    return ("{:+}%" if to_sign else "{}%").format(
        int(res) if res % 1 == 0 else res
    ) 


@decorators.rangetest(strict_range=False, percent=(0.0, 1.0))
def substract_percent(value: float, percent: float):
    return prettify_float(value - (value * percent))


def infinite_loop(func, *args, **kwargs):
    func = settings.logger.catch_error(func)
    while True:
        func(*args, **kwargs)
