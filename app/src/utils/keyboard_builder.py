from aiogram.types import (InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

delete_kb = ReplyKeyboardRemove

async def get_inline_buttons(
        *,
        btns: dict[str, str],
        sizes: tuple[int] = (2,)) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()


async def get_products_pagination(btns: list[tuple], page: int = 0, per_page: int = 1) -> InlineKeyboardMarkup:
        try:
            start_index = page * per_page
            end_index = start_index + per_page

            keyboard = InlineKeyboardBuilder()
            for name, product_id, _, _, _ in btns[start_index:end_index]:
                keyboard.row(InlineKeyboardButton(text='Добавить в корзину', callback_data=f'product_{product_id}'))

            previous_page = page > 0
            next_page = end_index < len(btns)

            navigation_buttons = []

            if previous_page:
                navigation_buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'page:{page - 1}'))

            if next_page:
                navigation_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{page + 1}"))

            if navigation_buttons:
                keyboard.row(*navigation_buttons)
            keyboard.row(InlineKeyboardButton(text='На главную 🔙', callback_data='to main'))
            return keyboard.as_markup()
        except Exception as e:
            raise e


async def get_reply_buttons(
        *btns: str,
        placeholder: str = None,
        request_contact: int = None,
        request_location: int = None,
        sizes: tuple[int] = (2,),
) -> ReplyKeyboardMarkup:
    '''
    Parameters request_contact and request_location must be as indexes of btns args for buttons you need.
    Example:
    get_keyboard(
            "Меню",
            "О магазине",
            "Варианты оплаты",
            "Варианты доставки",
            "Отправить номер телефона",
            placeholder="Что вас интересует?",
            request_contact=4,
            sizes=(2, 2, 1)
        )
    '''
    keyboard = ReplyKeyboardBuilder()

    for index, text in enumerate(btns, start=0):

        if request_contact and request_contact == index:
            keyboard.add(KeyboardButton(text=text, request_contact=True))

        elif request_location and request_location == index:
            keyboard.add(KeyboardButton(text=text, request_location=True))
        else:
            keyboard.add(KeyboardButton(text=text))

    return keyboard.adjust(*sizes).as_markup(
        resize_keyboard=True, input_field_placeholder=placeholder)


def get_delivery_options_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Указать адрес вручную 📝", callback_data='enter address manually')],
                [InlineKeyboardButton(text="Отправить местоположение 📳", callback_data='send location', request_location=True),
            ],
            [
                InlineKeyboardButton(text="Отмена ❌", callback_data='cancel_delete')
            ]
        ],
    )
    return keyboard


def get_confirm_order():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить заказ ✅", callback_data='confirm order'),
                InlineKeyboardButton(text="Отменить заказ ❌", callback_data='cancel order')
            ]
        ]
    )
    return keyboard


