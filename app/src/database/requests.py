from typing import List
import os

from sqlalchemy import select

from .models import Category, Product, Cart
from .engine import session_maker

# Взаимодействие с категорией
async def get_categories() -> Category:
    async with session_maker() as session:
        query = await session.scalars(select(Category))
        categories = query.all()
        return categories if categories else []


async def get_categorie_id(category_name: str) -> None:
    async with session_maker() as session:
        return await session.scalar(select(Category).where(Category.name == category_name))


async def create_categorie(name_category: str) -> None:
    async with session_maker() as session:
        new_category = Category(name=name_category)
        session.add(new_category)
        await session.commit()


async def change_categorie(category_id: int, category_name: str) -> None:
    async with session_maker() as session:
        result = await session.scalars(select(Category).where(Category.id == category_id))
        category = result.first()
        category.name = category_name
        await session.commit()


async def delete_categorie(category_id: int) -> None:
    async with session_maker() as session:
        result = await session.scalars(select(Category).where(Category.id == category_id))
        category = result.first()
        await session.delete(category)
        await session.commit()


# Взаимодействие с товаром
async def get_products(category_id: int) -> List[Product]:
    async with session_maker() as session:
        product = list(await session.scalars(select(Product).where(Product.category_id == category_id)))
        return product if product else []

async def get_product(product_id: int):
    async with session_maker() as session:
        return await session.scalar(select(Product).where(Product.id == product_id))

async def create_product(name: str, description: str, price: int, category_id: int, photo_path: str) -> None:
    async with session_maker() as session:
        new_product = Product(name=name, description=description, price=price, category_id=category_id, photo_path=photo_path)
        session.add(new_product)
        await session.commit()


async def delete_product(product_id: int) -> None:
    async with session_maker() as session:
        result = await session.scalars(select(Product).where(Product.id == product_id))
        category = result.first()
        product = await get_product(product_id)

        product_file = product.photo_path
        os.remove(product_file)

        await session.delete(category)
        await session.commit()


# Взаимодействие с корзиной
async def add_to_cart(user_id: int, product_id: int):
    async with session_maker() as session:
        cart = await session.scalar(select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id))
        if cart:
            cart.quantity += 1
            await session.commit()
            return cart
        else:
            session.add(Cart(user_id=user_id, product_id=product_id, quantity=1))
            await session.commit()


async def get_cart_product(user_id: int):
    async with session_maker() as session:
        cart = await session.scalars(select(Cart).where(Cart.user_id == user_id))
        return cart.all()


async def delete_product_from_cart(user_id: int, product_id: int):
    async with session_maker() as session:
        cart = await session.scalar(select(Cart).where(Cart.product_id == product_id))
        await session.delete(cart)
        await session.commit()
