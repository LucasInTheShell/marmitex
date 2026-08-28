from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.modules.auth.domain.entities import AccountRole


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    company_id: UUID | None
    role: AccountRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    account: AccountResponse


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    role: AccountRole
    company_id: UUID | None = None

    @model_validator(mode="after")
    def validate_company_scope(self):
        if self.role is AccountRole.COMPANY and self.company_id is None:
            raise ValueError("Usuários de empresa precisam estar vinculados a uma empresa.")
        if self.role is not AccountRole.COMPANY and self.company_id is not None:
            raise ValueError("Somente usuários de empresa podem possuir empresa vinculada.")
        return self
