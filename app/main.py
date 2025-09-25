from fastapi import FastAPI

from app.routers import categories, products


app = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)

# Подключение маршрутов категорий и товаров
app.include_router(categories.router)
app.include_router(products.router)


# Корневой endpoint для проверки
@app.get("/")
async def root():
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}
