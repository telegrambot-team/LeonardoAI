from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class DatabaseConnector:
    def __init__(self, url: str, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(url=url, echo=echo)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False
        )

    async def dispose(self) -> None:
        await self.engine.dispose()


def get_db(settings) -> DatabaseConnector:
    return DatabaseConnector(url=settings.postgres_db_url, echo=settings.echo)
