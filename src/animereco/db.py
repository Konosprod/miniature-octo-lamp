import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://user:password@localhost/dbname"
)


class Database:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.AsyncSessionLocal = async_sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine, class_=AsyncSession
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    @asynccontextmanager
    async def connect(self):
        async with self.engine.connect() as conn:
            try:
                yield conn
            except Exception:
                await conn.rollback()
                raise

    async def close(self):
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.AsyncSessionLocal = None

    @asynccontextmanager
    async def get_session(self):
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


db = Database()


async def get_session():
    async with db.get_session() as session:
        yield session
