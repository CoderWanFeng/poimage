"""Bounded lossless PNG IDAT optimizer."""

import struct
import zlib

from poimage.lib.image.png_chunks import (
    _DEFAULT_PNG_LIMITS,
    _PngFormatError,
    _parse_png,
)
from poimage.lib.image.png_filters import (
    _encode_rows,
    _filter_plans,
    _inflate_rows,
    _inflate_scanlines,
)


_FULL_FILTER_SEARCH_MAX_PIXELS = 256 * 256


_ZLIB_STRATEGIES = (
    zlib.Z_DEFAULT_STRATEGY,
    zlib.Z_FILTERED,
    zlib.Z_RLE,
)


def _png_chunk(chunk_type, payload):
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def _compress_scanlines(scanlines, strategy):
    compressor = zlib.compressobj(
        level=9,
        method=zlib.DEFLATED,
        wbits=zlib.MAX_WBITS,
        memLevel=9,
        strategy=strategy,
    )
    return compressor.compress(scanlines) + compressor.flush()


def _optimize_png_idat_losslessly(source, limits=None):
    """Return smaller PNG bytes, or ``None`` when no safe win exists."""
    if limits is None:
        limits = _DEFAULT_PNG_LIMITS
    try:
        document = _parse_png(source, limits=limits)
        pixel_count = document.width * document.height
        best_compressed = None

        if pixel_count <= _FULL_FILTER_SEARCH_MAX_PIXELS:
            rows, original_filters = _inflate_rows(document)
            original_scanlines = None
            scanline_candidates = (
                _encode_rows(
                    rows,
                    document.filter_bytes_per_pixel,
                    plan,
                )
                for plan in _filter_plans(
                    rows,
                    document.filter_bytes_per_pixel,
                    original_filters,
                )
            )
        else:
            rows = None
            original_scanlines = _inflate_scanlines(document)
            scanline_candidates = (original_scanlines,)

        for scanlines in scanline_candidates:
            for strategy in _ZLIB_STRATEGIES:
                compressed = _compress_scanlines(scanlines, strategy)
                if best_compressed is None or len(compressed) < len(best_compressed):
                    best_compressed = compressed

        if best_compressed is None:
            return None
        candidate = (
            source[:document.idat_start]
            + _png_chunk(b"IDAT", best_compressed)
            + source[document.idat_end:]
        )
        if len(candidate) >= len(source):
            return None

        candidate_document = _parse_png(candidate, limits=limits)
        if rows is None:
            if _inflate_scanlines(candidate_document) != original_scanlines:
                raise _PngFormatError("PNG scanlines changed")
        else:
            candidate_rows, _ = _inflate_rows(candidate_document)
            if candidate_rows != rows:
                raise _PngFormatError("PNG reconstructed rows changed")
        return candidate
    except (_PngFormatError, OSError, zlib.error):
        return None
