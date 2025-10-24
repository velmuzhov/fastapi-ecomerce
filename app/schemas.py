from typing import Annotated
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, HttpUrl, EmailStr, SecretStr


class BaseCategory(BaseModel):
    """
    Базовая модель для категории
    """

    name: Annotated[
        str,
        Field(
            min_length=3,
            max_length=50,
            description="Название категории (3-50 символов)",
        ),
    ]
    parent_id: Annotated[
        int | None,
        Field(
            default=None,
            description="ID родительской категории, если есть",
        ),
    ]


class CategoryCreate(BaseCategory):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """

    ...


class Category(BaseCategory):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """

    id: Annotated[int, Field(description="Уникальный идентификатор категории")]
    is_active: Annotated[bool, Field(description="Активность категории")]

    model_config = ConfigDict(from_attributes=True)


class BaseProduct(BaseModel):
    """
    Базовая модель для товара.
    """

    name: Annotated[
        str,
        Field(
            min_length=3,
            max_length=100,
            description="Название товара (3-100 символов)",
        ),
    ]
    description: Annotated[
        str,
        Field(
            default=None,
            max_length=500,
            description="Описание товара (до 500 символов)",
        ),
    ]
    price: Annotated[float, Field(gt=0, description="Цена товара (больше 0)")]
    image_url: Annotated[
        HttpUrl | None,
        Field(
            default=None,
            max_length=200,
            description="URL изображения товара",
        ),
    ]
    stock: Annotated[
        int, Field(ge=0, description="Количество товара на складе (0 или больше)")
    ]
    category_id: Annotated[
        int, Field(description="ID категории, к которой относится товар")
    ]


class ProductCreate(BaseProduct):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """

    ...


class Product(BaseProduct):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """

    id: Annotated[int, Field(description="Уникальный идентификатор товара")]
    is_active: Annotated[bool, Field(description="Активность товара")]

    model_config = ConfigDict(from_attributes=True)


class BaseUser(BaseModel):
    email: EmailStr = Field(description="Email пользователя")
    role: str = Field(
        default="buyer",
        pattern=r"^(buyer|seller)$",
        description="Роль: 'byuer' или 'seller'",
    )


class UserCreate(BaseUser):
    password: SecretStr = Field(min_length=8, description="Пароль (минимум 8 символов)")

    model_config = ConfigDict(from_attributes=True)


class User(BaseUser):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class BaseReview(BaseModel):
    """
    Базовая модель для отзывов. Служит для наследования. Не должна использоваться напрямую.
    """
    user_id: Annotated[
        int,
        Field(description="ID пользователя, оставившего отзыв"),
    ]
    product_id: Annotated[
        int,
        Field(description="ID товара, к которому относится отзыв")
    ]
    comment: Annotated[
        str | None,
        Field(
            description="Текст отзыва, необязательное",
            default=None,
        )
    ]
    comment_date: Annotated[
        datetime,
        Field(
            description="Дата и время создания отзыва, необязательное",
            default_factory=datetime.now,
        )
    ]
    is_active: Annotated[
        bool,
        Field(
            "Активен ли отзыв (для мягкого удаления)"б
        )
    ]

class ReviewCreate(BaseReview):
    """
    Входная модель для создания и обновления отзывов
    """
    ...

class Review(BaseReview):
    """
    Модель для возврата отзыва в HTTP-ответах
    """
    id: int

    model_config = ConfigDict(from_attributes=True)
