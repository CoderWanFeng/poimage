"""Route image compression requests to one internal handler."""

import os
from pathlib import Path

from PIL import Image

from poimage.lib.image.animated_gif_compression_handler import (
    _AnimatedGifCompressionHandler,
)
from poimage.lib.image.raster_image_compression_handler import (
    _RasterImageCompressionHandler,
)


class _ImageCompressionRouter:
    """Select exactly one handler for an image compression request."""

    @staticmethod
    def process(input_file: str, output_file: str, quality: int) -> None:
        input_path = os.fsdecode(input_file)
        output_path = os.fsdecode(output_file)

        if Path(output_path).suffix.lower() == ".gif":
            source = _ImageCompressionRouter._open_animated_gif(input_path)
            if source is not None:
                with source:
                    _AnimatedGifCompressionHandler.process(
                        source,
                        input_path,
                        output_path,
                    )
                return None

        _RasterImageCompressionHandler.process(
            input_path,
            output_path,
            quality,
        )

    @staticmethod
    def _open_animated_gif(input_file: str):
        try:
            source = open(input_file, "rb")
        except OSError:
            return None

        try:
            with Image.open(source) as image:
                is_animated_gif = (
                    image.format == "GIF"
                    and getattr(image, "is_animated", False)
                    and getattr(image, "n_frames", 1) > 1
                )
        except (OSError, Image.DecompressionBombError):
            source.close()
            return None

        if not is_animated_gif:
            source.close()
            return None

        source.seek(0)
        return source
