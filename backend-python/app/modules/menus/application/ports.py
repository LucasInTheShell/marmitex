from dataclasses import dataclass
from typing import Protocol

MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_MENU_ITEM_IMAGES = 6


@dataclass(frozen=True, slots=True)
class ImageSource:
    content: bytes
    content_type: str | None
    filename: str | None


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    content: bytes
    content_type: str
    extension: str
    width: int
    height: int


class InvalidImageContentError(Exception):
    pass


class ObjectStorageOperationError(Exception):
    pass


class ImageProcessor(Protocol):
    def process(self, source: ImageSource) -> ProcessedImage: ...


class ObjectStorage(Protocol):
    async def upload(self, key: str, content: bytes, content_type: str) -> None: ...

    async def delete(self, key: str) -> None: ...

    def public_url(self, key: str) -> str: ...
