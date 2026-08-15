"""Atomic writer for raster image compression requests."""

import os
from pathlib import Path

from PIL import Image

from poimage.lib.image.compression_path import (
    _create_temporary_file,
    _resolve_output_path,
    _target_mode,
)


class _RasterImageCompressionHandler:
    """Save non-animated image requests without damaging existing outputs."""

    @staticmethod
    def process(input_file: str, output_file: str, quality: int) -> None:
        requested_output_path = Path(output_file)
        output_path = _resolve_output_path(output_file)
        temporary_path = None

        try:
            with Image.open(input_file) as image:
                output_format = _RasterImageCompressionHandler._output_format(
                    requested_output_path
                )
                output_mode = _target_mode(output_path)
                suffix = requested_output_path.suffix or ".tmp"
                temporary_path, temporary = _create_temporary_file(
                    output_path,
                    suffix,
                )
                with temporary:
                    image.save(
                        temporary,
                        format=output_format,
                        quality=quality,
                    )
                    temporary.flush()
                    os.fsync(temporary.fileno())

            if output_mode is not None:
                os.chmod(str(temporary_path), output_mode)
            os.replace(str(temporary_path), str(output_path))
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _output_format(output_path: Path) -> str:
        extension = output_path.suffix.lower()
        try:
            return Image.registered_extensions()[extension]
        except KeyError:
            raise ValueError(
                "unknown file extension: {}".format(extension)
            )
