from typing import Protocol

from app.modules.companies.domain.entities import Company


class CompanyRepository(Protocol):
    async def list(self) -> list[Company]: ...

    async def create(
        self, name: str, email: str, password_hash: str
    ) -> Company: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

