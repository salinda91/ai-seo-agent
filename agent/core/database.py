from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

from sqlalchemy import text

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe column check/migration for SQLite:
        for col_def in [
            "local_repo_path VARCHAR(500)",
            "git_branch VARCHAR(100) DEFAULT 'main'",
            "git_remote VARCHAR(100) DEFAULT 'origin'"
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE websites ADD COLUMN {col_def}"))
            except Exception:
                pass
