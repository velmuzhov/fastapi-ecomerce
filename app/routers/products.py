from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import desc, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.db_depends import get_async_db

from app.models.users import User as UserModel
from app.auth import get_current_seller

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get(
    "/",
    response_model=ProductList,
    status_code=status.HTTP_200_OK,
)
async def get_all_products(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category_id: Annotated[
        int | None,
        Query(
            description="ID категории для фильтрации",
        ),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            description="Поиск по названию/описанию товара",
        ),
    ] = None,
    min_price: Annotated[
        float | None,
        Query(
            ge=0,
            description="Минимальная цена товара",
        ),
    ] = None,
    max_price: Annotated[
        float | None,
        Query(
            ge=0,
            description="Максимальная цена товара",
        ),
    ] = None,
    in_stock: Annotated[
        bool | None,
        Query(
            description="true - только товары в наличии, false - только без остатка",
        ),
    ] = None,
    seller_id: Annotated[
        int | None,
        Query(
            description="ID продавца для фильтрации",
        ),
    ] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает список всех товаров.
    """
    # products = db.scalars(
    #     select(ProductModel).where(ProductModel.is_active == True)
    # ).all()

    # result = await db.scalars(
    #     select(ProductModel)
    #     .join(CategoryModel)
    #     .where(
    #         ProductModel.is_active == True,
    #         CategoryModel.is_active == True,
    #     )
    # )

    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )

    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    # if search is not None:
    #     search_value = search.strip()
    #     if search_value:
    #         filters.append(func.lower(ProductModel.name).like(f"%{search_value.lower()}%"))
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)

    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    rank_col = None
    if search is not None:
        search_value = search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery("english", search_value)
            filters.append(ProductModel.tsv.op("@@")(ts_query))
            rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label("rank")
            total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    total = await db.scalar(total_stmt) or 0

    if rank_col is not None:
        products_stmt = (
            select(ProductModel, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(products_stmt)
        rows = result.all()
        items = [row[0] for row in rows]
    else:
        products_stmt = (
            select(ProductModel)
            .where(*filters)
            .order_by(ProductModel.id)
            .limit(page_size)
        )
        items = (await db.scalars(products_stmt)).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post(
    "/",
    response_model=ProductSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller),
):
    """
    Создает новый товар, привязанный к текущему продавцу (только для "seller")
    """
    category = await db.scalar(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True,
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found",
        )

    product_to_db = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(product_to_db)
    await db.commit()
    await db.refresh(product_to_db)

    return product_to_db


@router.get(
    "/category/{category_id}",
    response_model=list[ProductSchema],
    status_code=status.HTTP_200_OK,
)
async def get_products_by_category(
    category_id: int, db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список товаров в указанной категории по ее ID.
    """
    category = await db.scalar(
        select(CategoryModel).where(
            CategoryModel.id == category_id,
            CategoryModel.is_active == True,
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    result = await db.scalars(
        select(ProductModel).where(
            ProductModel.category_id == category_id,
            ProductModel.is_active == True,
        )
    )

    return result.all()


@router.get(
    "/{product_id}",
    response_model=ProductSchema,
    status_code=status.HTTP_200_OK,
)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    product = await db.scalar(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    category = await db.scalar(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True,
        )
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found",
        )

    return product


@router.put(
    "/{product_id}",
    response_model=ProductSchema,
    status_code=status.HTTP_200_OK,
)
async def update_product(
    product_id: int,
    new_data: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller),
):
    """
    Обновляет товар по его ID, если он принадлежит текущему продавцу
    (только для "seller").
    """
    product = await db.scalar(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products",
        )

    category = await db.scalar(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True,
        )
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found",
        )

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**new_data.model_dump())
    )
    await db.commit()
    await db.refresh(product)

    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProductSchema,
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller),
):
    """
    Выполняет мягкое удаление товара по его ID, если он принадлежит
    текущему продавцу (только для "seller")
    """
    product = await db.scalar(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own products",
        )

    category = await db.scalar(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id,
            CategoryModel.is_active == True,
        )
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found",
        )

    product.is_active = False
    await db.commit()
    await db.refresh(product)

    return product
