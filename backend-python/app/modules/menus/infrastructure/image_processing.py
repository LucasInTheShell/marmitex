import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.menus.application.ports import (
    MAX_IMAGE_UPLOAD_BYTES,
    ImageProcessor,
    ImageSource,
    InvalidImageContentError,
    ProcessedImage,
)

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_PIXELS = 50_000_000
MAX_IMAGE_SIZE = (1200, 900)


class PillowImageProcessor(ImageProcessor):
    def process(self, source: ImageSource) -> ProcessedImage:
        if not source.content or len(source.content) > MAX_IMAGE_UPLOAD_BYTES:
            raise InvalidImageContentError("A imagem deve ter no máximo 5 MB.")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(source.content)) as original:
                    if original.format not in ALLOWED_FORMATS:
                        raise InvalidImageContentError(
                            "Use uma imagem no formato JPEG, PNG ou WebP."
                        )
                    if original.width * original.height > MAX_IMAGE_PIXELS:
                        raise InvalidImageContentError("A resolução da imagem é muito alta.")
                    image = ImageOps.exif_transpose(original)
                    image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
                    image = self._to_rgb(image)
                    output = BytesIO()
                    image.save(output, format="WEBP", quality=82, method=6)
                    return ProcessedImage(
                        content=output.getvalue(),
                        content_type="image/webp",
                        extension="webp",
                        width=image.width,
                        height=image.height,
                    )
        except InvalidImageContentError:
            raise
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombWarning,
        ) as error:
            raise InvalidImageContentError("O arquivo não contém uma imagem válida.") from error

    @staticmethod
    def _to_rgb(image: Image.Image) -> Image.Image:
        has_alpha = image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        )
        if not has_alpha:
            return image.convert("RGB")
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        return Image.alpha_composite(background, rgba).convert("RGB")
