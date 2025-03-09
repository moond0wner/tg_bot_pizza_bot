from pydantic import BaseModel, Field, ConfigDict, field_validator
from PIL import Image as PILImage
from io import BytesIO

class CategorySchema(BaseModel):
    name: str = Field(max_length=15, title='Название категории')

    model_config = ConfigDict(extra='forbid')


class ProductSchema(BaseModel):
    name: str = Field(max_length=15, title='Название товара', description='Полное наименование товара')

    model_config = ConfigDict(extra='forbid')

class DescriptionProductSchema(ProductSchema):
    description: str = Field(max_length=100)

    model_config = ConfigDict(extra='forbid')

class PriceProductSchema(ProductSchema):
    price: float = Field(gt=0)

    model_config = ConfigDict(extra='forbid')

class ImageProductSchema(ProductSchema):
    image_data: bytes

    @field_validator('image_data')
    def validate_image(cls, data: bytes):
        try:
            img = PILImage.open(BytesIO(data))
            if img.format not in ['JPEG', 'PNG', 'JPG']:
                raise ValueError('Неверный формат изображения. Только JPEG, JPG и PNG может быть использовано.')
            img.verify()
            img.close()
            return data
        except Exception as e:
            raise ValueError(f'Неверное изображение: {e}')
