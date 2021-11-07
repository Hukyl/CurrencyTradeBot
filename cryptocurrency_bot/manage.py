import os
import sqlite3
import threading
import sys
from time import sleep

import schedule
import argparse

from configs import settings
from models.user import User, Session
from models.logger import Logger, cprint
from utils import dt
from utils import infinite_loop


def is_valid_file(parser, arg, *, ext: str = None, check_exists: bool = True):
    if check_exists and not os.path.exists(arg):
        parser.error(f"The file {arg} does not exist!")
    elif ext and os.path.splitext(arg)[1] != ext:
        parser.error(f"The file {arg} has wrong extension!")
    else:
        return arg


def runbot(level: str):
    import main_bot
    targets = [
        main_bot.schedule_thread,
        main_bot.bot.infinity_polling,
    ]
    settings.logger.set_level(level)
    for target in targets:
        threading.Thread(
            target=infinite_loop, args=(target,), daemon=True
        ).start()
    main_bot.settings.logger.info("Bot started")
    while True:
        try:
            sleep(100000)
        except KeyboardInterrupt:
            break
    schedule.clear()
    main_bot.settings.logger.info("Bot stopped")


def check_subscribed(ids: list):
    for user_id in ids:
        if not User.exists(user_id):
            cprint(f"FAILURE: No user found by id: {user_id}", "red")
            continue
        user = User(user_id)
        if user.is_pro:
            cprint(
                "SUCCESS: User {} IS subscribed until {} UTC".format(
                    user_id,
                    dt.convert_to_country_format(user.is_pro, 'ru')
                ),
                "green"
            )
        else:
            cprint(f"SUCCESS: User {user_id} IS NOT subscribed", "green")


def give_staff(ids: list):
    for user_id in ids:
        if not User.exists(user_id):
            cprint(f"FAILURE: No user found by id: {user_id}", "red")
            continue
        user = User(user_id)
        if user.is_staff:
            cprint(
                f"FAILURE: User {user_id} already has a staff membership", 
                "red"
            )
        else:
            user.init_staff()
            cprint(
                f"SUCCESS: User {user_id} received a staff membership", 
                "green"
            )


def remove_staff(ids: list):
    for user_id in ids:
        if not User.exists(user_id):
            cprint(f"FAILURE: No user found by id: {user_id}", "red")
            continue
        user = User(user_id)
        if not user.is_staff:
            cprint(f"FAILURE: User {user_id} has no staff membership", "red")
        else:
            user.delete_staff()
            cprint(
                f"SUCCESS: User {user_id} doesn't have a staff membership now",
                "green"
            )


def get_notification_count(ids: list):
    for user_id in ids:
        if not User.exists(user_id):
            cprint(f"FAILURE: No user found by id: {user_id}", "red")
            continue
        session = Session(user_id)
        cprint(
            "SUCCESS: User {} has {} notifications left".format(
                user_id, session.free_notifications_count
            ), 
            "green"
        )


def set_notification_count(user_id: int, count: int):
    if not User.exists(user_id):
        cprint(f"FAILURE: No user found by id: {user_id}", "red")
        sys.exit(1)
    session = Session(user_id)
    session.set_count(count)
    cprint(
        f"SUCCESS: User {user_id} notification count has been set to {count}", 
        "green"
    )


def create_db_dump(db_filename: str, dump_filename: str):
    with sqlite3.connect(db_filename) as conn:
        with open(dump_filename, 'w') as file:
            for line in conn.iterdump():
                file.write("%s\n" % line)
    cprint("SUCCESS: dump was created successfully", "green")


def load_db_dump(dump_filename: str, db_filename: str):
    if os.path.isfile(db_filename):
        os.remove(db_filename)
    with sqlite3.connect(db_filename) as conn:
        with open(dump_filename, 'r') as file:
            conn.executescript(file.read())
    cprint("SUCCESS: database was created successfully", "green")


if __name__ == '__main__':
    commands = {
        'run': lambda namespace: runbot(namespace.level),
        'check-subscribed': lambda namespace: check_subscribed(namespace.ids),
        'give-staff': lambda namespace: give_staff(namespace.ids),
        'remove-staff': lambda namespace: remove_staff(namespace.ids),
        'get-notification-count': lambda namespace: get_notification_count(
            namespace.ids
        ),
        'set-notification-count': lambda namespace: set_notification_count(
            namespace.user_id, namespace.count
        ),
        'create-db-dump': lambda namespace: create_db_dump(
            namespace.db, namespace.dump
        ),
        'load-db-dump': lambda namespace: load_db_dump(
            namespace.dump, namespace.db
        ),
    }

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="command", dest='command')
    parser_run = subparsers.add_parser('run', help='run the bot')
    parser_run.add_argument(
        "-l", "--level", default="info", 
        help="set logger level", type=str, choices=list(Logger.LOG_LEVELS)
    )
    parser_subscribed = subparsers.add_parser(
        'check-subscribed', help="check whether user(s) are subscribed"
    )
    parser_subscribed.add_argument(
        'ids', metavar='user_id', type=int, nargs="+"
    )
    parser_give_staff = subparsers.add_parser(
        'give-staff', help="give staff membership to users"
    )
    parser_give_staff.add_argument(
        'ids', metavar='user_id', type=int, nargs="+"
    )
    parser_remove_staff = subparsers.add_parser(
        'remove-staff', help="remove staff membership from users"
    )
    parser_remove_staff.add_argument(
        'ids', metavar='user_id', type=int, nargs="+"
    )
    parser_get_count = subparsers.add_parser(
        'get-notification-count', help="get notifications count for users"
    )
    parser_get_count.add_argument(
        'ids', metavar='user_id', type=int, nargs="+"
    )
    parser_set_count = subparsers.add_parser(
        'set-notification-count', help="set new notifications count"
    )
    parser_set_count.add_argument('user_id', type=int)
    parser_set_count.add_argument('count', type=int)
    parser_create_dump = subparsers.add_parser(
        'create-db-dump', help="create database dump"
    )
    parser_create_dump.add_argument(
        '--db', help="database filename",
        default=settings.DB_NAME, required=False,
        type=lambda x: is_valid_file(parser_create_dump, x, ext='.sqlite3')
    )
    parser_create_dump.add_argument(
        '--dump', help="dump filename",
        default=settings.DUMP_NAME, required=False,
        type=lambda x: is_valid_file(
            parser_create_dump, x, ext='.sql', check_exists=False
        )
    )
    parser_load_dump = subparsers.add_parser(
        'load-db-dump', help="load database from dump"
    )
    parser_load_dump.add_argument(
        '--dump', help="dump filename",
        default=settings.DUMP_NAME, required=False,
        type=lambda x: is_valid_file(parser_create_dump, x, ext='.sql')
    )
    parser_load_dump.add_argument(
        '--db', help="database filename",
        default=settings.DB_NAME, required=False,
        type=lambda x: is_valid_file(
            parser_create_dump, x, ext='.sqlite3', check_exists=False
        )
    )
    namespace = parser.parse_args()
    if len(namespace.__dict__) > 1:
        commands[namespace.command](namespace)
    else:
        parser.print_help()
