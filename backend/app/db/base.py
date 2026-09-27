import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.app.config import settings


# Ensure SQLite path directory exists if using SQLite
if "sqlite" in settings.DATABASE_URL:
    db_file_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    if db_file_path and db_file_path != ":memory:":
        db_dir = os.path.dirname(os.path.abspath(db_file_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
