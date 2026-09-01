import asyncio
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from app.core.config import Settings
from app.modules.menus.application.ports import (
    ObjectStorage,
    ObjectStorageOperationError,
)


class LocalObjectStorage(ObjectStorage):
    def __init__(self, root: str, public_base_url: str) -> None:
        self.root = Path(root).resolve()
        self.public_base_url = public_base_url.rstrip("/")

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        del content_type
        target = self._target(key)
        try:
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(target.write_bytes, content)
        except OSError as error:
            raise ObjectStorageOperationError("Falha ao gravar a imagem.") from error

    async def delete(self, key: str) -> None:
        target = self._target(key)
        try:
            await asyncio.to_thread(target.unlink, missing_ok=True)
        except OSError as error:
            raise ObjectStorageOperationError("Falha ao excluir a imagem.") from error

    def public_url(self, key: str) -> str:
        encoded_key = "/".join(quote(part, safe="") for part in PurePosixPath(key).parts)
        return f"{self.public_base_url}/{encoded_key}"

    def _target(self, key: str) -> Path:
        posix_key = PurePosixPath(key)
        if posix_key.is_absolute() or ".." in posix_key.parts:
            raise ObjectStorageOperationError("Chave de armazenamento inválida.")
        target = (self.root / Path(*posix_key.parts)).resolve()
        if not target.is_relative_to(self.root):
            raise ObjectStorageOperationError("Chave de armazenamento inválida.")
        return target


class S3ObjectStorage(ObjectStorage):
    def __init__(self, settings: Settings) -> None:
        import boto3
        from botocore.config import Config

        assert settings.storage_public_base_url is not None
        self.bucket = settings.storage_bucket
        self.public_base_url = settings.storage_public_base_url.rstrip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            region_name=settings.storage_region,
            aws_access_key_id=settings.storage_access_key_id,
            aws_secret_access_key=settings.storage_secret_access_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
        except Exception as error:
            raise ObjectStorageOperationError("Falha ao enviar a imagem.") from error

    async def delete(self, key: str) -> None:
        try:
            await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)
        except Exception as error:
            raise ObjectStorageOperationError("Falha ao excluir a imagem.") from error

    def public_url(self, key: str) -> str:
        encoded_key = "/".join(quote(part, safe="") for part in PurePosixPath(key).parts)
        return f"{self.public_base_url}/{encoded_key}"


def build_object_storage(settings: Settings) -> ObjectStorage:
    if settings.storage_backend == "s3":
        return S3ObjectStorage(settings)
    assert settings.storage_public_base_url is not None
    return LocalObjectStorage(
        settings.storage_local_path,
        settings.storage_public_base_url,
    )
