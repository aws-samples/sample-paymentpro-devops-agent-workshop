"""Database session management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.effective_database_url, echo=settings.environment == "dev")
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session_factory() as session:
        yield session
