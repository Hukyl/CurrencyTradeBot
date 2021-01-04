import threading
import sys
from time import sleep
import datetime

import techsupport_bot
import main_bot
from utils._datetime import get_current_datetime



def infinite_loop(func, *args, **kwargs):
    while True:
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(repr(e))
        else:
            break



if __name__ == '__main__':
    targets = [
        main_bot.check_alarm_times,
        main_bot.update_rates,
        main_bot.check_premium_ended,
        main_bot.verify_predictions,
        techsupport_bot.main,
        main_bot.bot.infinity_polling,
    ]
    for target in targets:
        threading.Thread(target=target, daemon=True).start()
    print(f"[INFO] Bot started at {str(get_current_datetime(0).time().strftime('%H:%M:%S'))}")
    while True:
        try:
            sleep(100000)
        except KeyboardInterrupt:
            print(f"[INFO] Bot stopped at {str(get_current_datetime(0).time().strftime('%H:%M:%S'))}")
            sys.exit(0)
