"""Native lossless handler for animated GIF compression requests."""

import os
import shutil

from poimage.lib.image.compression_path import (
    _create_temporary_file,
    _resolve_output_path,
    _target_mode,
)
from poimage.lib.image.gif_blocks import _DEFAULT_GIF_LIMITS
from poimage.lib.image.gif_optimizer import (
    _optimize_image_data_losslessly,
)


class _AnimatedGifCompressionHandler:
    """Optimize GIF image data or preserve the original bytes."""

    @staticmethod
    def process(source, input_file: str, output_file: str) -> None:
        if _AnimatedGifCompressionHandler._is_same_file(
            source,
            input_file,
            output_file,
        ):
            return None

        source.seek(0)
        source_bytes = source.read(_DEFAULT_GIF_LIMITS.max_input_bytes + 1)
        candidate = None
        if len(source_bytes) <= _DEFAULT_GIF_LIMITS.max_input_bytes:
            candidate = _optimize_image_data_losslessly(source_bytes)

        source.seek(0)
        _AnimatedGifCompressionHandler._write_atomically(
            source,
            output_file,
            candidate,
        )

    @staticmethod
    def _is_same_file(source, input_path: str, output_path: str) -> bool:
        normalized_input = os.path.abspath(os.path.normpath(input_path))
        normalized_output = os.path.abspath(os.path.normpath(output_path))
        if normalized_input == normalized_output:
            return True

        try:
            return os.path.samestat(os.fstat(source.fileno()), os.stat(output_path))
        except OSError:
            return False

    @staticmethod
    def _write_atomically(source, output_file: str, candidate) -> None:
        output_path = _resolve_output_path(output_file)
        output_mode = _target_mode(output_path)
        temporary_path = None

        try:
            temporary_path, temporary = _create_temporary_file(
                output_path,
                ".tmp",
            )
            with temporary:
                if candidate is None:
                    shutil.copyfileobj(source, temporary)
                else:
                    temporary.write(candidate)
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
