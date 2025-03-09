import os
from typing import Union

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext


from ..utils.keyboard_builder import get_inline_buttons
from ..database.requests import create_categorie, get_categories, change_categorie, delete_categorie
from ..database.requests import create_product, get_products, get_product, delete_product

from ..utils.admin_checker import AdminChecker


FOLDER = 'images'

admin = Router()
admin.message.filter(F.chat.type == 'private', AdminChecker())


class AddCategory(StatesGroup):
    name = State()

class ChangeCategory(StatesGroup):
    category_id = State()
    old_name = State()
    new_name = State()

class DeleteCategory(StatesGroup):
    category_name = State()

class DeleteProduct(StatesGroup):
    product_name = State()
    category_id = State()

class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    category_id = State()
    photo = State()


# Старт
@admin.callback_query(F.data == 'to main admin')
@admin.message(Command('admin'))
async def start(event: Union[Message, CallbackQuery]):
    buttons = {"Категория": "category", "Товар": "product"}
    if isinstance(event, Message):
        await event.answer(
            f"Здравствуйте, администратор <b>{event.from_user.full_name}</b>, выберите раздел взаимодействия.\n"
            f"<i>Будьте аккуратны с изменениями, неправильное действие может плохо отразиться на работе пиццерии.</i>",
            reply_markup=await get_inline_buttons(btns=buttons),
            parse_mode='HTML'
        )

    else:
        await event.answer()
        await event.message.answer(
            f"Здравствуйте, администратор <b>{event.from_user.full_name}</b>, выберите раздел взаимодействия.\n"
            f"<i>Будьте аккуратны с изменениями, неправильное действие может плохо отразиться на работе пиццерии.</i>",
            reply_markup=await get_inline_buttons(btns=buttons),
            parse_mode='HTML'
        )



# Выбор изменения
@admin.callback_query(F.data == 'category')
async def _(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("<b>Выберите действие</b>",
                         reply_markup=await get_inline_buttons(
                             btns={"Список категорий": 'list category',
                                   "Добавить категорию": 'new category',
                                   "Изменить категорию": 'change category',
                                   "Удалить категорию": 'delete category',
                                   "Отмена": 'to main admin'}),
                         parse_mode='HTML'
                                 )


@admin.callback_query(F.data == 'product')
async def _(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("<b>Выберите действие</b>",
                         reply_markup=await get_inline_buttons(
                             btns={"Список товаров": 'list product',
                                   "Добавить товар": 'new product',
                                   "Удалить товар": 'delete product'}),
                        parse_mode = 'HTML'
                                )


# Список категорий
@admin.callback_query(F.data == 'list category')
async def _(callback: CallbackQuery):
    categories = await get_categories()
    print(categories, type(categories))
    if categories:
        await callback.answer()
        result = '\n'.join(f'{index}. {category['name']}' for index, category in enumerate(categories, start=1))
        await callback.message.edit_text(f'Список категорий: <b>\n{result}</b>', parse_mode='HTML',
                                         reply_markup=await get_inline_buttons(btns={'Отмена': 'to main admin'}))
    else:
        await callback.answer("Категории отсутствуют ❗")


# Добавление категории
@admin.callback_query(F.data == 'new category')
async def _(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategory.name)
    await callback.answer()
    await callback.message.answer("<i>Введите название категории...</i>", parse_mode='HTML')


@admin.message(AddCategory.name, F.text)
async def _(message: Message, state: FSMContext):
    try:
        await create_categorie(message.text)
        await message.answer(f'Категория <b>"{message.text}"</b> добавлена 👌', parse_mode='HTML')
        await state.clear()
    except Exception as e:
        await message.answer(f"<i>Произошла ошибка: {e}</i>", parse_mode='HTML')
        raise e



# Изменение категории
@admin.callback_query(F.data == 'change category')
async def _(callback: CallbackQuery, state: FSMContext):
    categories = await get_categories()
    if categories:
        await callback.answer()
        categories_buttons = {category["name"]: f'change_category_{category["id"]}' for category in categories}
        await state.set_state(ChangeCategory.category_id)
        await callback.message.answer("<b>Выберите категорию которую хотите изменить</b>",
                             reply_markup=await get_inline_buttons(btns=categories_buttons),
                             parse_mode='HTML')
    else:
        await callback.answer("Список категорий отсутствует, добавьте хотя бы одну категорию ❗")


@admin.callback_query(ChangeCategory.category_id, F.data.startswith('change_category_'))
async def _(callback: CallbackQuery, state: FSMContext):
    category_id = callback.data.split('_')[-1]
    await state.update_data(category_id=category_id)
    await callback.answer()
    await state.set_state(ChangeCategory.new_name)
    await callback.message.edit_text("<i>Введите новое название для категории...</i>", parse_mode='HTML')


@admin.message(ChangeCategory.new_name)
async def _(message: Message, state: FSMContext):
    await state.update_data(new_name=message.text)
    data = await state.get_data()
    try:
        await change_categorie(data['category_id'], data['new_name'])
        await message.answer("<b>Категория успешно изменена</b> 👌", parse_mode='HTML',
                             reply_markup=await get_inline_buttons(btns={"Отмена": 'to main admin'}))
        await state.clear()
    except Exception as e:
        await message.answer("<i>Произошла ошибка в ходе изменения категории</i>", parse_mode='HTML',
                                reply_markup=await get_inline_buttons(btns={'Отмена': 'to main admin'}))
        await state.clear()
        raise e


# Удаление категории
@admin.callback_query(F.data == 'delete category')
async def _(callback: CallbackQuery):
    categories = await get_categories()
    if categories:
        await callback.answer()
        categories_buttons = {category['name']: f'delete_category_{category['id']}' for category in categories}
        await callback.message.answer("<b>Выберите категорию которую хотите удалить</b>",
                             reply_markup=await get_inline_buttons(btns=categories_buttons),
                             parse_mode='HTML')
    else:
        await callback.answer("<i>Список категорий отсутствует, добавьте хотя бы одну категорию</i>", parse_mode='HTML')


@admin.callback_query(F.data.startswith('delete_category_'))
async def _(callback: CallbackQuery):
    data = callback.data.split('_')[-1]
    await callback.answer()
    try:
        await delete_categorie(data)
        await callback.message.edit_text("<b>Категория успешно удалена</b> 👌", parse_mode='HTML',
                                         reply_markup=await get_inline_buttons(btns={'На главную': 'to main admin'}))
    except Exception as e:
        await callback.message.edit_text("<i>Произошла ошибка в ходе удаления категории...</i>", parse_mode='HTML',
                                         reply_markup=await get_inline_buttons(btns={'На главную': 'to main admin'}))
        raise e


# Список товаров
@admin.callback_query(F.data == 'list product')
async def _(callback: CallbackQuery):
    categories = await get_categories()
    if categories:
        await callback.answer()
        categories_buttons = {category['name']: f'items_category_{category['id']}' for category in categories}
        await callback.message.answer(
            "<b>Выберите категорию товаров</b>",
            reply_markup=await get_inline_buttons(btns=categories_buttons),
            parse_mode='HTML'
        )
    else:
        await callback.answer("<i>Список категорий отсутствует, добавьте хотя бы одну категорию</i>", parse_mode='HTML')


@admin.callback_query(F.data.startswith('items_'))
async def _(callback: CallbackQuery):
    data = callback.data.split('_')[-1]
    products = await get_products(data)
    await callback.answer()
    if products:
        result = '\n'.join(f'Название: {product['name']}\nОписание: {product['description']}\nЦена: {product['price']}' for product in products)
        await callback.message.answer(f"<b>Список товаров:</b> \n{result}", parse_mode='HTML')
    else:
        await callback.answer("<i>Список товаров отсутствует, добавьте хотя бы один товар</i>", parse_mode='HTML')


# Добавление товара
@admin.callback_query(F.data == 'new product')
async def _(callback: CallbackQuery, state: FSMContext):
    categories = await get_categories()
    if categories:
        await callback.answer()
        categories_buttons = {category['name']: f'choose_category:{category['id']}' for category in categories}
        await state.set_state(AddProduct.category_id)
        await callback.message.edit_text("<b>Выберите категорию в которую хотите добавить товар</b>",
                             reply_markup=await get_inline_buttons(btns=categories_buttons),
                             parse_mode='HTML'
                             )
    else:
        await callback.answer("Список категорий отсутствует, добавьте хотя бы одну категорию")


@admin.callback_query(AddProduct.category_id, F.data.startswith('choose_category:'))
async def _(callback: CallbackQuery, state: FSMContext):
    category_id = callback.data.split(':')[-1]
    await state.update_data(category_id=category_id)
    await callback.answer()
    await callback.message.edit_text("<i>Введите название товара</i>", parse_mode='HTML')
    await state.set_state(AddProduct.name)


@admin.message(AddProduct.name)
async def _(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("<i>Введите описание товара</i>", parse_mode='HTML')
    await state.set_state(AddProduct.description)


@admin.message(AddProduct.description)
async def _(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("<i>Введите цену товара в рублях</i>", parse_mode='HTML')
    await state.set_state(AddProduct.price)


@admin.message(AddProduct.price)
async def get_photo(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("<i>Отправьте фотографию товара</i>", parse_mode='HTML')
    await state.set_state(AddProduct.photo)


@admin.message(AddProduct.photo, F.photo)
async def _(message: Message, state: FSMContext, bot: Bot):
    try:
        await message.answer("<i>Данные приняты, создаю товар...</i> ⏳", parse_mode='HTML')

        file_id = message.photo[-1].file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        downloaded_file = await bot.download_file(file_path)

        os.makedirs(FOLDER, exist_ok=True)
        photo_path = f'{FOLDER}/{message.photo[-1].file_unique_id}.jpg'
        with open(photo_path, 'wb') as f:
            f.write(downloaded_file.read())

        data = await state.get_data()
        name = data.get('name', 'N/A')
        des = data.get('description', 'N/A')
        price = data.get('price', 'N/A')
        cat_id = data.get("category_id", 'N/A')
        await create_product(name, des, int(price), int(cat_id), photo_path)
        answer = (
            f'Был успешно добавлен товар "{name}"\n'
            f'Описание: {des}\n'
            f'Цена: {price} RUB'
        )
        await bot.send_photo(chat_id=message.from_user.id, caption=answer, photo=FSInputFile(photo_path),
                             reply_markup=await get_inline_buttons(btns={'На главную': 'to main admin'}))
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка в ходе добавления товара.",
                             reply_markup=await get_inline_buttons(btns={'На главную': 'to main admin'}))
        await state.clear()
        raise e


@admin.message(AddProduct.photo)
async def _(message: Message, state: FSMContext):
    await message.answer("Вы отправили неверные данные, попробуйте заново")
    await get_photo(message, state)


# Удаление товара
@admin.callback_query(F.data == 'delete product')
async def _(callback: CallbackQuery, state: FSMContext):
    categories = await get_categories()
    if categories:
        await callback.answer()
        await state.set_state(DeleteProduct.category_id)
        categories_buttons = {category['name']: f'choose_category_{category['id']}' for category in categories}
        await callback.message.edit_text(
            "<b>Выберите категорию товара</b>",
            reply_markup=await get_inline_buttons(btns=categories_buttons),
            parse_mode='HTML'
        )
    else:
        await callback.answer("<i>Список категорий отсутствует, добавьте хотя бы одну категорию</i>", parse_mode='HTML')


@admin.callback_query(DeleteProduct.category_id, F.data.startswith('choose_category_'))
async def _(callback: CallbackQuery, state: FSMContext):
    category_id = callback.data.split('_')[-1]
    await state.update_data(category_id=int(category_id))
    products = await get_products(category_id)
    if products:
        products_buttons = {product['name']: f'delete_product_{product['id']}' for product in products}
        await callback.message.answer("<b>Выберите товар который хотите удалить</b>",
                             reply_markup=await get_inline_buttons(btns=products_buttons)
                             )
    else:
        await callback.answer("Список категорий отсутствует, добавьте хотя бы одну категорию")


@admin.callback_query(F.data.startswith('delete_product_'))
async def _(callback: CallbackQuery, state: FSMContext):
    product_id = callback.data.split('_')[-1]
    data = await state.get_data()
    category_id = data.get('category_id')
    product = await get_product(product_id)
    try:
        await delete_product(product_id, category_id)
        await callback.message.answer(f'<b>Товар "{product['name']}" успешно удалён</b>', parse_mode='HTML',
                                      reply_markup=await get_inline_buttons(btns={'На главную': 'to main admin'}))
    except Exception as e:
        await callback.message.answer("<i>В ходе удаления товара возникла ошибка, обратитесь к разработчику</i>",
                                      parse_mode='HTML',
                                      reply_markup=await get_inline_buttons(btns={'На главную': 'to main admin'}))
        raise e


