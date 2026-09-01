from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mavi Connect API"
    environment: str = "development"
    database_url: str
    session_ttl_hours: int = Field(default=168, ge=1, le=24 * 90)
    employee_session_ttl_hours: int = Field(default=12, ge=1, le=24)
    app_time_zone: str = "America/Sao_Paulo"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    storage_backend: Literal["local", "s3"] = "local"
    storage_bucket: str = "dish-images"
    storage_local_path: str = "data/media"
    storage_public_base_url: str | None = None
    storage_endpoint_url: str | None = None
    storage_region: str = "us-east-1"
    storage_access_key_id: str | None = None
    storage_secret_access_key: str | None = None

    @field_validator("database_url")
    @classmethod
    def validate_postgres_url(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return value

    @field_validator("app_time_zone")
    @classmethod
    def validate_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("APP_TIME_ZONE must be a valid IANA timezone") from error
        return value

    @model_validator(mode="after")
    def validate_storage_configuration(self) -> "Settings":
        if self.storage_backend == "local" and not self.storage_public_base_url:
            self.storage_public_base_url = "http://localhost:8000/media"
        if self.storage_backend == "s3" and not all(
            (
                self.storage_endpoint_url,
                self.storage_access_key_id,
                self.storage_secret_access_key,
                self.storage_public_base_url,
            )
        ):
            raise ValueError(
                "S3 storage requires endpoint, access key, secret key and public base URL"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
