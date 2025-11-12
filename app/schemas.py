from decimal import Decimal
from typing import Annotated
from datetime import datetime
from fastapi import Form
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
        str | None,
        Field(
            default=None,
            max_length=500,
            description="Описание товара (до 500 символов)",
        ),
    ]
    price: Annotated[Decimal, Field(gt=0, description="Цена товара (больше 0)")]
    # image_url: Annotated[
    #     str | None,
    #     Field(
    #         default=None,
    #         max_length=200,
    #         description="URL изображения товара",
    #     ),
    # ]
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

    @classmethod
    def as_form(
        cls,
        name: Annotated[str, Form()],
        price: Annotated[Decimal, Form()],
        stock: Annotated[int, Form()],
        category_id: Annotated[int, Form()],
        description: Annotated[str | None, Form()] = None,
    ) -> "ProductCreate":
        return cls(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
        )


class Product(BaseProduct):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """

    id: Annotated[int, Field(description="Уникальный идентификатор товара")]
    is_active: Annotated[bool, Field(description="Активность товара")]
    rating: Annotated[float, Field(description="Средний рейтинг товара")]

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

    product_id: Annotated[
        int, Field(description="ID товара, к которому относится отзыв")
    ]
    comment: Annotated[
        str | None,
        Field(
            description="Текст отзыва, необязательное",
            default=None,
        ),
    ]
    grade: Annotated[
        int,
        Field(
            description="Оценка товара, целое число от 1 до 5",
            ge=1,
            le=5,
        ),
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
    user_id: Annotated[
        int,
        Field(description="ID пользователя, оставившего отзыв"),
    ]
    comment_date: Annotated[
        datetime,
        Field(
            description="Дата и время создания отзыва, необязательное",
            default_factory=datetime.now,
        ),
    ]
    is_active: Annotated[
        bool,
        Field(
            description="Активен ли отзыв (для мягкого удаления)",
        ),
    ]

    model_config = ConfigDict(from_attributes=True)


class ProductList(BaseModel):
    """
    Список пагинации для товаров
    """

    items: list[Product] = Field(description="Товары для текущей страницы")
    total: int = Field(ge=0, description="Общее количество товаров")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")

    model_config = ConfigDict(from_attributes=True)


class CartItemBase(BaseModel):
    product_id: int = Field(description="ID товара")
    quantity: int = Field(ge=1, description="Количество товара")


class CartItemCreate(CartItemBase):
    """Модель для добавления нового товара в корзину"""

    pass


class CartItemUpdate(BaseModel):
    """Модель для обновления количества товара в корзине"""

    quantity: int = Field(..., ge=1, description="Новое количество товара")


class CartItem(BaseModel):
    """Товар в корзине с данными продукта"""

    id: int = Field(..., description="ID позиции корзины")
    quantity: int = Field(..., ge=1, description="Количество товара")
    product: Product = Field(..., description="Информация о товаре")

    model_config = ConfigDict(from_attributes=True)


class Cart(BaseModel):
    """Полная информация о корзине пользователя"""

    user_id: int = Field(..., description="ID пользователя")
    items: list[CartItem] = Field(
        default_factory=list, description="Содержимое корзины"
    )
    total_quantity: int = Field(..., ge=0, description="Общее количество товаров")
    total_price: Decimal = Field(..., ge=0, description="Общая стоимость товаров")

    model_config = ConfigDict(from_attributes=True)


class OrderItem(BaseModel):
    id: int = Field(description="ID позиции заказа")
    product_id: int = Field(description="ID товара")
    quantity: int = Field(ge=1, description="Количество")
    unit_price: Decimal = Field(ge=0, description="Цена за единицу на момент покупки")
    total_price: Decimal = Field(ge=0, description="Сумма по позиции")
    product: Product | None = Field(
        description="Полная информация о товаре", default=None
    )

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    id: int = Field(description="ID заказа")
    user_id: int = Field(description="ID пользователя")
    status: str = Field(description="Текущий статус заказа")
    total_amount: Decimal = Field(ge=0, description="Общая стоимость")
    created_at: datetime = Field(description="Когда заказ был создан")
    updated_at: datetime = Field(description="Когда последний раз обновлялся")
    items: list[OrderItem] = Field(default_factory=list, description="Список позиций")

    model_config = ConfigDict(from_attributes=True)


class OrderList(BaseModel):
    items: list[Order] = Field(description="Заказы на текущей странице")
    total: int = Field(ge=0, description="Общее количество заказов")
    page: int = Field(ge=1, description="Текущая страница")
    page_size: int = Field(ge=1, description="Размер страницы")

    model_config = ConfigDict(from_attributes=True)
