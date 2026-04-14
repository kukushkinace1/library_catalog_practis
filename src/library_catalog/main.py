"""
Точка входа FastAPI приложения Library Catalog.
"""

from fastapi import FastAPI

# Создать приложение
app = FastAPI(
    title="Library Catalog API",
    description="REST API для управления библиотечным каталогом",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {"message": "Welcome to Library Catalog API"}


@app.get("/health")
async def health_check():
    """Health check эндпоинт."""
    return {"status": "healthy"}


# Для запуска через python -m
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)