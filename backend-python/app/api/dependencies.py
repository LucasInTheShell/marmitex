from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from psycopg import AsyncConnection

from app.core.database import Database


async def connection(request: Request) -> AsyncIterator[AsyncConnection]:
    database: Database = request.app.state.database
    async with database.pool.connection() as database_connection:
        yield database_connection


DatabaseConnection = Annotated[AsyncConnection, Depends(connection)]
