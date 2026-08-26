from app.modules.companies.domain.entities import Company
from app.modules.companies.domain.exceptions import (
    CompanyConflictError,
    DuplicateCompanyEmailError,
)
from app.modules.companies.domain.repositories import CompanyRepository, PasswordHasher


class CompanyApplicationService:
    def __init__(
        self, repository: CompanyRepository, password_hasher: PasswordHasher
    ) -> None:
        self.repository = repository
        self.password_hasher = password_hasher

    async def list(self) -> list[Company]:
        return await self.repository.list()

    async def create(self, name: str, email: str, password: str) -> Company:
        try:
            return await self.repository.create(
                name, email.lower(), self.password_hasher.hash(password)
            )
        except DuplicateCompanyEmailError as error:
            raise CompanyConflictError from error

