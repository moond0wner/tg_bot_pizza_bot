import os
from typing import Union

from aiogram import Router, F, Bot
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile, LabeledPrice, PreCheckoutQuery, \
    SuccessfulPayment
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from ..utils.keyboard_builder import (get_inline_buttons, get_products_pagination,
                                      get_delivery_options_keyboard, get_confirm_order)
from ..database.requests import (get_categories, get_products, get_product,
                                 add_to_cart, get_cart_product, delete_product_from_cart)


user = Router()

class UserChoose(StatesGroup):
    choose_category = State()
    products_data = State()
    page_product = State()


class PlaceAnOrder(StatesGroup):
    payment = State()
    delivery_method = State()
    waiting_for_address_option = State()
    enter_address = State()
    payment_method = State()
    order_confirmation = State()


@user.message(F.text == 'Назад ⬅')
@user.callback_query(F.data == 'to main')
@user.message(CommandStart())
async def start(event: Union[Message, CallbackQuery]):
    buttons = {"Меню 📖": 'menu', "Корзина 🗑": 'cart', "Наши адреса 🏪": 'my_address', "О нас 📑": "about_us"}

    if isinstance(event, Message):
        await event.answer(
            f'Здравствуйте, <b>{event.from_user.full_name}</b> 🖐. \n'
            f'Я бот пиццерии "Название", благодаря мне Вы сможете удобно и быстро заказать пиццу!\n'
            "Выберите, что Вас интересует",
            reply_markup=await get_inline_buttons(btns=buttons)
        )
    else:
        await event.answer()
        await event.message.answer(
            f'Здравствуйте, <b>{event.from_user.full_name}</b> 🖐. \n'
            f'Я бот пиццерии "Название", благодаря мне Вы сможете удобно и быстро заказать пиццу!\n'
            "Выберите, что Вас интересует",
            reply_markup=await get_inline_buttons(btns=buttons)
        )



@user.callback_query(F.data == 'menu')
async def _(callback: CallbackQuery, state: FSMContext):
    categories = await get_categories()
    categories_buttons = {category.name: f'category_{category.id}' for category in categories}
    await state.set_state(UserChoose.choose_category)
    await callback.answer()
    await callback.message.answer(
        "Выберите категорию пицц",
        reply_markup=await get_inline_buttons(btns=categories_buttons)
    )


@user.callback_query(F.data == 'my_address')
async def _(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer('Наша пиццерия находится по адресу <b>Адрес</b>\n\n'
                                  'или же..\n\n'
                                  'Сеть нашей пиццерии находятся по адресу:\n'
                                  '<b>Адрес 1</b>\n'
                                  '<b>Адрес 2</b>\n'
                                  '<b>Адрес N..</b>',
                                  reply_markup=await get_inline_buttons(btns={"На главную 🔙": 'to main'}),
                                  parse_mode='HTML')

@user.callback_query(F.data == 'about_us')
async def _(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer('<i>Тут должно быть описание заведения...</i>',
                                  reply_markup=await get_inline_buttons(btns={"На главную 🔙": 'to main'}),
                                  parse_mode='HTML')



@user.callback_query(F.data.startswith('category_'))
async def _(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = callback.data.split('_')[1]

    await state.update_data(choose_category=data)

    products = await get_products(data)
    products_data = [(product.name, product.id, product.description, product.price, product.photo_path) for product in products]
    await state.update_data(products_data=products_data)

    data = await state.get_data()
    page = data.get("page_product", 0)

    if products_data:
        name, _, description, price, photo_path = products_data[page]
        if not os.path.exists(photo_path):
            await callback.answer("Произошла ошибка, не найдена фотография ❗", show_alert=True)
            await state.clear()
            return
        try:
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=FSInputFile(photo_path),
                caption=f"{name}\n{description}\nЦена: {price} руб.",
                reply_markup=await get_products_pagination(btns=products_data, page=0),
                parse_mode='HTML'
            )
            await callback.answer("Выберите пиццу из категории")
            await callback.answer()
        except FileNotFoundError as e:
            await callback.answer("Извините, вышла ошибка: Изображение товара не найдено ❗", show_alert=True)
            await state.clear()
            raise e
        except Exception as e:
            await state.clear()
            raise e
    else:
        await callback.message.answer("В данной категории пока нет товаров ❗")
        await state.clear()
        await callback.answer()


@user.callback_query(F.data.startswith('product_'))
async def _(callback: CallbackQuery):
    data = callback.data.split('_')[1]
    await add_to_cart(callback.from_user.id, data)
    await callback.answer("Товар добавлен в корзину ✅")


@user.callback_query(F.data.startswith('page:'))
async def _(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(':')[1])
    data = await state.get_data()
    products_data = data.get("products_data", [])
    await state.update_data(page_product=page)

    if products_data:
        try:
            name, _, description, price, photo_path = products_data[page]
            await callback.message.edit_media(
                media=InputMediaPhoto(media=FSInputFile(photo_path), caption=f'{name}\n{description}\nЦена: {price} руб.',
                parse_mode = 'HTML'),
                reply_markup=await get_products_pagination(btns=products_data, page=page),
            )
            await callback.answer()
        except FileNotFoundError:
            await callback.message.answer(f"<i>Извините, вышла ошибка: Изображение для товара не найдено</i> ❗",
                                          parse_mode='HTML')
        except Exception as e:
            raise e
    else:
        await callback.answer()
        await callback.message.answer("<i>Извините, данные о товарах не найдены</i> ❗",
                                      parse_mode='HTML',
                                      reply_markup=await get_inline_buttons(btns={"На главную 🔙": 'to main'}))


@user.callback_query(F.data == 'cart')
async def display_cart(callback: CallbackQuery, state: FSMContext):
    await update_cart_message(callback, state)


async def update_cart_message(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    sum_of_payment = 0
    user_id = callback.from_user.id
    cart = await get_cart_product(user_id)

    if not cart:
        await callback.message.edit_text("Ваша корзина пуста.",
                                         reply_markup=await get_inline_buttons(btns={"На главную 🔙": 'to main'}))
        return

    text = "🛒 Ваша корзина:\n"
    for item in cart:
        product = await get_product(item.product_id)
        if product:
            product_name = product.name
            quantity = int(item.quantity)
            payment = product.price * quantity
            sum_of_payment += payment
            text += f'🍕Товар: {product_name} - {quantity} шт. \n💰Сумма - {payment} руб.\n\n'

    await state.set_state(PlaceAnOrder.payment)
    await state.update_data(payment=sum_of_payment)
    text += f'💳Общая сумма к оплате: {sum_of_payment} руб.'

    buttons = {'Перейти к оплате 💸': 'go to pay', 'Удалить товар ❌': 'choose_delete', "Отмена ❌": 'to main'}
    await callback.message.edit_text(text, reply_markup=await get_inline_buttons(btns=buttons))



@user.callback_query(F.data == 'go to pay')
async def go_to_pay(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите тип доставки...",
                                  reply_markup=await get_inline_buttons(
                                      btns={"Доставка 🛵": 'delivery', "Самовывоз 🚶": 'pickup',
                                            "Отмена ❌": 'cancel_delete'}))
    await state.set_state(PlaceAnOrder.delivery_method)


@user.callback_query(PlaceAnOrder.delivery_method, F.data == 'cancel delete')
async def _(callback: CallbackQuery, state: FSMContext):
    await go_to_pay(callback, state)
    await callback.answer("Действие отменено. ✅")


@user.callback_query(F.data == 'choose_delete')
async def _(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart = await get_cart_product(user_id)
    text = "🛒 Выберите что хотите удалить:\n"
    keyboard = []
    for item in cart:
        product = await get_product(item.product_id)
        if product:
            product_name = product.name
            keyboard.append([f'❌{product_name}', f'delete_product:{item.product_id}'])

    keyboard.append(["Отмена ❌", 'cancel_delete'])


    await callback.message.edit_text(text, reply_markup=await get_inline_buttons(btns=dict(keyboard)))
    await callback.answer()


@user.callback_query(F.data.startswith('delete_product:'))
async def delete_product(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    product_id = int(callback.data.split(':')[1])
    await delete_product_from_cart(user_id, product_id)
    await update_cart_message(callback, state)
    await callback.answer("Товар удален. ✅")


@user.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await update_cart_message(callback, state)
    await callback.answer("Действие отменено. ✅")


@user.callback_query(PlaceAnOrder.delivery_method, F.data == 'delivery')
async def _(callback: CallbackQuery, state: FSMContext):
    await state.update_data(delivery_method=callback.data)
    await state.set_state(PlaceAnOrder.payment_method)
    await callback.message.edit_text("Выберите способ оплаты",
                         reply_markup=await get_inline_buttons(
                             btns={"Онлайн картой 💳": 'online card', "Наличными курьеру 💰": 'cash to courier'}))


@user.callback_query(PlaceAnOrder.delivery_method, F.data == 'pickup')
async def _(callback: CallbackQuery, state: FSMContext):
    await state.update_data(delivery_method=callback.data)
    await state.set_state(PlaceAnOrder.payment_method)
    await callback.message.edit_text("Выберите способ оплаты",
                         reply_markup=await get_inline_buttons(
                             btns={"Онлайн картой 💳": 'online card', "Наличными в пиццерии 💰": 'cash in pizzeria'}))


@user.callback_query(PlaceAnOrder.payment_method, F.data == 'online card')
async def _(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_method=callback.data)
    data = await state.get_data()
    if data['delivery_method'] == 'delivery':
        await callback.message.edit_text("Выберите способ указания адреса:",
                             reply_markup=get_delivery_options_keyboard())
        await state.set_state(PlaceAnOrder.waiting_for_address_option)  # Ожидаем выбора опции адреса
    else:  # data["delivery_method"] == "Самовывоз"
        #Пропускаем запрос адреса и сразу переходим к подтверждению заказа
        await display_order_confirmation(callback, state)

@user.callback_query(PlaceAnOrder.payment_method, F.data.startswith('cash'))
async def _(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_method=callback.data)
    data = await state.get_data()
    if data['delivery_method'] == 'delivery':
        await callback.message.edit_text("Выберите способ указания адреса:",
                                         reply_markup=get_delivery_options_keyboard())
        await state.set_state(PlaceAnOrder.waiting_for_address_option)  # Ожидаем выбора опции адреса
    else:  # data["delivery_method"] == "Самовывоз"
        # Пропускаем запрос адреса и сразу переходим к подтверждению заказа
        await display_order_confirmation(callback, state)


@user.callback_query(PlaceAnOrder.waiting_for_address_option, F.data == 'enter address manually')
async def _(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите адрес для доставки", reply_markup=None)
    await state.set_state(PlaceAnOrder.enter_address)


@user.callback_query(PlaceAnOrder.waiting_for_address_option, F.location, F.data == 'send location')
async def _(message: Message, state: FSMContext):
    latitude = message.location.latitude
    longitude = message.location.longitude
    await state.update_data(latitude=latitude, longitude=longitude)
    # TODO: Call geocoder to translate coordinate to address (optional)
    await display_order_confirmation(message, state)


@user.message(PlaceAnOrder.enter_address, F.text)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(enter_address=message.text)

    # TODO: Validate Address format (optional)
    await display_order_confirmation(message, state)


async def display_order_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    payment = data.get('payment', 'N/A')
    delivery = data.get('delivery_method', 'N/A')
    payment_method = data.get('payment_method', 'N/A')
    address = data.get("enter_address", 'N/A')

    if delivery == 'delivery': delivery = "Доставка 🛵"
    else: delivery = 'Самовывоз 🚶'

    if payment_method == 'online card': payment_method = 'Онлайн картой 💳'
    elif payment_method == 'cash to courier': payment_method = 'Наличными курьеру 💰'
    else: payment_method = 'Наличными в пиццерии 💰'

    # Handle cases where address is location (TODO)
    latitude = data.get("latitude", None)
    longitude = data.get("longitude", None)

    if latitude and longitude:
        address = f"Широта: {latitude}, Долгота: {longitude}"

    await message.answer("Хорошо, <b>данные получены</b>, давайте проверим их: \n\n"
                         f"Сумма к оплате: {payment} руб.\n"
                         f"Способ доставки: {delivery}\n"
                         f"Способ оплаты: {payment_method}\n"
                         f"Адрес: {address}\n\n"
                         f"Если всё правильно, <b>подтвердите заказ</b>",
                         parse_mode='HTML', reply_markup=get_confirm_order())


@user.callback_query(F.data == 'confirm order')
async def _(callback: CallbackQuery, bot: Bot, state: FSMContext):
    data = await state.get_data()
    await callback.answer("Отлично, переходим к оплате... 💸")
    await bot.send_invoice(chat_id=callback.from_user.id,
                           title='Оплата заказа в пиццерии',
                           description='Оплатите заказ',
                           provider_token=os.getenv('PAY_TOKEN'),
                           is_flexible=False,
                           currency='RUB',
                           prices=[LabeledPrice(label='Оплата заказа', amount=int(data['payment']) * 100)],
                           start_parameter='pay_order',
                           payload=f'order_{callback.from_user.id}'
                           ) # 4242 4242 4242 4242

@user.pre_checkout_query()
async def _(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@user.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def _(message: Message):
    payment_info = message.successful_payment
    await message.answer("Оплата прошла успешно ✅\nСтатус своего заказа вы можете посмотреть в главном меню.")

    # Дополнительный код:
    # 1. Добавить в меню кнопку просмотра статуса
    # 2. Отсылать заказ после оплаты в чат
    # 3. Сохранять информацию о транзакции в БД.



@user.callback_query(F.data == 'cancel order')
async def _(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Заказ отменен ✅")
    await update_cart_message(callback, state)

