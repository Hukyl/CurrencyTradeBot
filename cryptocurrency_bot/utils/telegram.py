from telebot import types


__all__ = ['kbs', 'inline_kbs']


def kbs(buttons, one_time_keyboard=True, row_width: int = None):
    """
    Creates a Telegram Keyboard
    :param buttons:
    :param one_time_keyboard:
    :param row_width:
    :return:
    """
    row_width = row_width or len(buttons)//2
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=one_time_keyboard, 
        row_width=row_width
    )
    if len(buttons) > 1:
        kb.add(*[types.KeyboardButton(i) for i in buttons])
    else:
        kb = None
    return kb


def inline_kbs(buttons: dict, row_width: int = 3):
    markup = types.InlineKeyboardMarkup(row_width=row_width)
    buttons = [
        types.InlineKeyboardButton(
            str(i), 
            callback_data=buttons[i]
        )
        for i in buttons
    ]
    markup.add(*buttons)
    return markup
