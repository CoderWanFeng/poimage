"""Format-aware lossless compression for path-based PNG inputs."""

import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from poimage.lib.image.png_chunks import _DEFAULT_PNG_LIMITS
from poimage.lib.image.png_optimizer import _optimize_png_idat_losslessly


def _replace_output_atomically(input_path, output_path, write_data):
    """Write a complete replacement beside the output, then atomically swap it in."""
    output_path = Path(output_path)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            write_data(stream)
            stream.flush()
            os.fsync(stream.fileno())
        mode_source = output_path if output_path.exists() else Path(input_path)
        shutil.copymode(mode_source, temporary_path)
        os.replace(temporary_path, output_path)
    except BaseException:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _write_png_bytes(input_path, output_path, data):
    _replace_output_atomically(
        input_path, output_path, lambda stream: stream.write(data)
    )


def _copy_png_file(input_path, output_path):
    if Path(input_path) == Path(output_path):
        return
    with open(input_path, "rb") as source:
        _replace_output_atomically(
            input_path,
            output_path,
            lambda destination: shutil.copyfileobj(source, destination),
        )


def _try_compress_png(input_file, output_file):
    """Handle PNG-to-PNG path requests without changing the public API."""
    try:
        input_path = Path(os.fsdecode(input_file))
        output_path = Path(os.fsdecode(output_file))
    except TypeError:
        return False

    if output_path.suffix.lower() != ".png":
        return False

    # Content detection keeps JPEG->PNG and other conversions on Pillow's
    # existing path while allowing PNG files with a non-.png input suffix.
    with Image.open(input_path) as image:
        if image.format != "PNG":
            return False
        image.verify()

    source_size = input_path.stat().st_size
    if source_size > _DEFAULT_PNG_LIMITS.max_baseline_bytes:
        _copy_png_file(input_path, output_path)
        return True

    source = input_path.read_bytes()
    candidate = _optimize_png_idat_losslessly(source)
    selected = candidate if candidate is not None else source
    if input_path == output_path and selected == source:
        return True
    _write_png_bytes(input_path, output_path, selected)
    return True
