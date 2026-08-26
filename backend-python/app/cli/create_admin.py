import argparse
import asyncio
import getpass

from psycopg import AsyncConnection

from app.core.config import get_settings
from app.modules.auth.infrastructure.password import ArgonPasswordService


async def create_admin(name: str, email: str, password: str) -> None:
    settings = get_settings()
    async with await AsyncConnection.connect(settings.database_url) as connection:
        await connection.execute(
            """
            insert into accounts (name, email, password_hash, role)
            values (%s, %s, %s, 'admin')
            """,
            (name, email.lower(), ArgonPasswordService().hash(password)),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Mavi Connect admin account")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Password: ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters")
    asyncio.run(create_admin(args.name, args.email, password))


if __name__ == "__main__":
    main()
