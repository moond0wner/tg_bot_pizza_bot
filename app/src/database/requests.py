from typing import List, Optional
import os
import json

from sqlalchemy import select

from .models import Category, Product, Cart, User
from .engine import session_maker
from ..database.redis_connection import redis
from ..utils.logger import Logger


# Взаимодействие с пользователем
async def is_user_exists(user_id: int) -> bool:
    """
    Проверяет, есть ли пользователь в БД
    """
    try:
        res = await redis.get(name=f'is_user_exists: {str(user_id)}')
        if not res:
            async with session_maker() as session:
                query_result = await session.scalar(select(User).where(User.telegram_id == user_id))
                await redis.set(name=f'is_user_exists: {str(user_id)}', value=1 if query_result else 0, ex=3600)
                return bool(query_result)

        return bool(res)
    except Exception as e:
        Logger.error(f"Ошибка при проверки наличия пользователя в БД: {e}")
        raise e


async def add_user(user_id: int, name: str, username: str, phone: str = 'не указан') -> None:
    """
    Добавляет пользователя в БД
    """
    try:
        async with session_maker() as session:
            new_user = User(
                telegram_id=user_id,
                name=name,
                username=username,
                phone=phone
            )
            session.add(new_user)
            await session.commit()
    except Exception as e:
        Logger.exception(f'Ошибка при добавлении пользователя: {e}')
        await session.rollback()
        raise e


# Взаимодействие с категорией
async def get_categories() -> dict:
    """
    Возвращает все категории товаров
    """
    try:
        categories_json = await redis.get(name=f'categories')
        if categories_json:
            categories = json.loads(categories_json.decode('utf-8'))
        else:
            async with session_maker() as session:
                query = await session.scalars(select(Category))
                categories = query.all()
                categories = [{'name': c.name, 'id': c.id} for c in categories]
                categories_json = json.dumps(categories)
                await redis.set('categories', categories_json)
        return categories
    except Exception as e:
        Logger.error(f'Ошибка при обращении к get_categories: {e}')
        raise e


async def get_categorie_id(category_name: str) -> Optional[int]:
    """
    Возвращает айди выбранной категории
    """
    try:
        category_id = await redis.get(name=f'categorie_id:{category_name}')
        if not category_id:
            async with session_maker() as session:
                category_id = await session.scalar(select(Category).where(Category.name == category_name))
                await redis.set(f'category_id:{category_name}', category_id)
        return category_id
    except Exception as e:
        Logger.error(f"Ошибка при обращении к get_categorie_id: {e}")
        raise e


async def create_categorie(name_category: str) -> None:
    """
    Создаёт новую категорию товаров
    """
    try:
        async with session_maker() as session:
            new_category = Category(name=name_category)
            session.add(new_category)
            await session.commit()
            await redis.delete('categories')
    except Exception as e:
        Logger.error(f'Ошибка при обращении к create_categorie: {e}')
        raise e


async def change_categorie(category_id: int, category_name: str) -> None:
    """
    Изменяет название категории
    """
    try:
        async with session_maker() as session:
            result = await session.scalars(select(Category).where(Category.id == int(category_id)))
            category = result.first()
            category.name = category_name
            await session.commit()
            await redis.delete('categories')
    except Exception as e:
        Logger.error(f'Ошибка при обращении к change_categorie: {e}')
        raise e


async def delete_categorie(category_id: int) -> None:
    """
    Удаляет категорию
    """
    try:
        async with session_maker() as session:
            result = await session.scalars(select(Category).where(Category.id == int(category_id)))
            category = result.first()
            await session.delete(category)
            await session.commit()
            await redis.delete('categories')
    except Exception as e:
        Logger.error(f'Ошибка при обращении к delete_categorie: {e}')
        raise e


# Взаимодействие с товаром
async def get_products(category_id: int) -> List[Product]:
    """
    Возвращает список товаров по определенной категории
    """
    try:
        products_json = await redis.get(f'products_on_category:{category_id}')
        if products_json:
            products = json.loads(products_json.decode('utf-8'))
        else:
            async with session_maker() as session:
                products = await session.scalars(select(Product).where(Product.category_id == int(category_id)))
                products = [
                    {
                     'name': c.name,
                     'description': c.description,
                     'id': c.id,
                     'price': c.price
                     }
                    for c in products.all()
                ]
                products_json = json.dumps(products)
                await redis.set(f'products_on_category:{category_id}', products_json)
        return products
    except Exception as e:
        Logger.error(f'Ошибка при обращении к get_products: {e}')
        raise e


async def get_product(product_id: int) -> Product:
    """
    Возвращает модель товара, чтобы в последующем обращаться к его значениям
    """
    try:
        product_json = await redis.get(f'product:{product_id}')
        if product_json:
            product = json.loads(product_json.decode('utf-8'))
        else:
            async with session_maker() as session:
                product = await session.scalar(select(Product).where(Product.id == int(product_id)))
                product = {
                           'name': product.name,
                           'description': product.description,
                           'price': product.price,
                           'id': product.id,
                           'photo_path': product.photo_path
                           }

                product_json = json.dumps(product)
                await redis.set(f'product:{product_id}', product_json)
        return product
    except Exception as e:
        Logger.error(f'Ошибка при обращении к get_product: {e}')
        raise e


async def create_product(name: str, description: str, price: int, category_id: int, photo_path: str) -> None:
    """
    Создаёт новый товар в определенной категории по заданным параметрам
    """
    try:
        async with session_maker() as session:
            new_product = Product(name=name,
                                  description=description,
                                  price=price,
                                  category_id=category_id,
                                  photo_path=photo_path)
            session.add(new_product)
            await session.commit()
            await redis.delete(f'products_on_category:{category_id}')
    except Exception as e:
        Logger.error(f'Ошибка при обращении к create_product: {e}')
        raise e


async def delete_product(product_id: int, category_id: int) -> None:
    """
    Удаляет товар (что тут еще сказать xD)
    """
    try:
        async with session_maker() as session:
            product = await session.get(Product, int(product_id))
            if product:
                product_file = product.photo_path
                if product_file and os.path.exists(product_file):
                    try:
                        os.remove(product_file)
                    except Exception as e:
                        Logger.error(f'Ошибка при удалении файла: {e}')


                await session.delete(product)
                await session.commit()

                await redis.delete(f'products_on_category:{category_id}')
                await redis.delete(f'product:{product_id}')
    except Exception as e:
        Logger.error(f'Ошибка при обращении к delete_product: {e}')
        raise e


# Взаимодействие с корзиной
async def create_user_cart(user_id: int, product_id: int, quantity: int = 1) -> None:
    """
    Создает новую запись в таблице Cart для указанного пользователя и товара.
    """
    try:
        async with session_maker() as session:
            cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
            session.add(cart_item)
            await session.commit()
    except Exception as e:
        Logger.error(f'Ошибка при обращении к create_user_cart: {e}')
        raise e


async def add_product_to_cart(user_id: int, product_id: int):
    """
    Увеличивает количество товара на единицу если есть корзина, иначе передает параметры функции для создания корзины
    """
    try:
        async with session_maker() as session:
            cart = await session.scalar(select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id))
            if cart:
                cart.quantity += 1
            else:
                await create_user_cart(user_id, product_id)
            await session.commit()
    except Exception as e:
        Logger.error(f'Ошибка при обращении к add_to_cart: {e}')
        raise e


async def get_cart_product(user_id: int) -> List[Cart]:
    """
    Возвращает модель корзины пользователя, к которой можно обращаться по её данным
    """
    try:
        cart = await redis.get(f'cart_for_user:{user_id}')
        if not cart:
            async with session_maker() as session:
                cart = await session.scalars(select(Cart).where(Cart.user_id == user_id))
                cart = cart.all()
        return cart
    except Exception as e:
        Logger.error(f"Ошибка при обращении к get_cart_product: {e}")
        raise e


async def delete_product_from_cart(user_id: int, product_id: int) -> None:
    """
    Удаляет продукт из корзины пользователя
    """
    try:
        async with session_maker() as session:
            query = await session.scalar(select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id))
            await session.delete(query)
            await session.commit()
    except Exception as e:
        Logger.error(f'Ошибка при обращении к delete_product_from_cart: {e}')
        raise e