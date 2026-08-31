from psycopg import AsyncConnection

from app.modules.operations.domain.entities import OperationalSettings


class PostgresOperationalSettingsRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def get(self) -> OperationalSettings:
        result = await self.connection.execute(
            """
            select order_cutoff_lead_minutes, updated_at
            from operational_settings
            where id = 1
            """
        )
        row = await result.fetchone()
        if row is None:
            raise RuntimeError("Operational settings row is missing")
        return OperationalSettings(**row)

    async def update_cutoff_lead(self, minutes: int) -> OperationalSettings:
        result = await self.connection.execute(
            """
            update operational_settings
            set order_cutoff_lead_minutes = %s,
                updated_at = now()
            where id = 1
            returning order_cutoff_lead_minutes, updated_at
            """,
            (minutes,),
        )
        row = await result.fetchone()
        if row is None:
            raise RuntimeError("Operational settings row is missing")
        return OperationalSettings(**row)
