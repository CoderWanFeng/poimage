"""Shared output-path policy for image compression handlers."""

import os
from pathlib import Path
import secrets
import stat


def _resolve_output_path(output_file: str) -> Path:
    requested_path = Path(output_file)
    if requested_path.is_symlink():
        return requested_path.resolve()
    return requested_path


def _target_mode(output_path: Path):
    try:
        return stat.S_IMODE(output_path.stat().st_mode)
    except FileNotFoundError:
        return None


def _create_temporary_file(output_path: Path, suffix: str):
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    for _ in range(100):
        temporary_path = output_path.parent / ".{}-{}{}".format(
            output_path.name,
            secrets.token_hex(8),
            suffix,
        )
        try:
            descriptor = os.open(str(temporary_path), flags, 0o666)
        except FileExistsError:
            continue

        try:
            return temporary_path, os.fdopen(descriptor, "w+b")
        except OSError:
            os.close(descriptor)
            try:
                temporary_path.unlink()
            except OSError:
                pass
            raise

    raise FileExistsError("unable to create a unique temporary output file")
