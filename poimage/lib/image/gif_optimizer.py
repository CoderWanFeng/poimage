"""Native lossless GIF optimization candidate arbitration."""

from poimage.lib.image.gif_blocks import _GifFormatError, _scan_gif
from poimage.lib.image.gif_frame_optimizer import (
    _build_i2_candidate,
    _build_palette_compaction_candidate,
    _build_palette_dedup_candidate,
    _build_transparent_i2_candidate,
    _validate_i2_candidate,
    _validate_palette_compaction,
    _validate_transparent_i2,
)
from poimage.lib.image.gif_frames import (
    _GifFrameError,
    _parse_gif_document,
)
from poimage.lib.image.gif_image_data_optimizer import (
    _build_i0_candidate,
    _build_i1_candidate,
    _optimal_packet_count,
    _validate_i1_candidate,
)
from poimage.lib.image.gif_lzw import (
    _DEFAULT_LZW_LIMITS,
    _GifLzwError,
)


def _optimize_image_data_subblocks(data, limits=None):
    """Return a strictly smaller I0 candidate, or None when none is safe."""
    try:
        image_spans = _scan_gif(data, limits=limits)
    except _GifFormatError:
        return None
    return _build_i0_candidate(data, image_spans)


def _optimize_image_data_losslessly(data, limits=None, lzw_limits=None):
    """Return the smallest verified I0/I1/I2 candidate, or None."""
    if lzw_limits is None:
        lzw_limits = _DEFAULT_LZW_LIMITS
    try:
        image_spans = _scan_gif(data, limits=limits)
    except _GifFormatError:
        return None

    best = _build_i0_candidate(data, image_spans)
    palette_candidate = None
    try:
        source_document = _parse_gif_document(data, limits=limits)
        palette_candidate = _build_palette_dedup_candidate(
            data,
            source_document,
        )
        if palette_candidate is not None and len(palette_candidate) < len(data):
            if best is None or len(palette_candidate) < len(best):
                best = palette_candidate
    except (_GifFormatError, _GifFrameError):
        palette_candidate = None

    try:
        i1_candidate = _build_i1_candidate(
            data,
            image_spans,
            lzw_limits,
        )
        if (
            len(i1_candidate) < len(data)
            and (best is None or len(i1_candidate) < len(best))
        ):
            _validate_i1_candidate(
                data,
                i1_candidate,
                image_spans,
                limits,
                lzw_limits,
            )
            best = i1_candidate
    except (_GifFormatError, _GifLzwError):
        pass

    try:
        document = _parse_gif_document(data, limits=limits)
        i2_candidate = _build_i2_candidate(
            data,
            document,
            lzw_limits,
        )
        if (
            len(i2_candidate) < len(data)
            and (best is None or len(i2_candidate) < len(best))
        ):
            _validate_i2_candidate(
                data,
                i2_candidate,
                limits,
                lzw_limits,
            )
            best = i2_candidate
    except (_GifFormatError, _GifFrameError, _GifLzwError):
        pass

    transparent_source = palette_candidate or data
    try:
        compact_document = _parse_gif_document(
            transparent_source,
            limits=limits,
        )
        compact_candidate, compact_mapping = (
            _build_palette_compaction_candidate(
                transparent_source,
                compact_document,
                lzw_limits,
            )
        )
        if (
            compact_candidate is not None
            and len(compact_candidate) < len(data)
            and (best is None or len(compact_candidate) < len(best))
        ):
            _validate_palette_compaction(
                transparent_source,
                compact_candidate,
                compact_mapping,
                limits,
                lzw_limits,
            )
            best = compact_candidate
    except (_GifFormatError, _GifFrameError, _GifLzwError):
        pass

    try:
        transparent_document = _parse_gif_document(
            transparent_source,
            limits=limits,
        )
        transparent_candidate = _build_transparent_i2_candidate(
            transparent_source,
            transparent_document,
            lzw_limits,
        )
        if len(transparent_candidate) < len(data):
            _validate_transparent_i2(
                transparent_source,
                transparent_candidate,
                limits,
                lzw_limits,
            )
            if best is None or len(transparent_candidate) < len(best):
                best = transparent_candidate
            compact_candidate, mapping = _build_palette_compaction_candidate(
                transparent_candidate,
                _parse_gif_document(transparent_candidate, limits=limits),
                lzw_limits,
            )
            if (
                compact_candidate is not None
                and len(compact_candidate) < len(data)
                and (best is None or len(compact_candidate) < len(best))
            ):
                _validate_palette_compaction(
                    transparent_candidate,
                    compact_candidate,
                    mapping,
                    limits,
                    lzw_limits,
                )
                best = compact_candidate
    except (_GifFormatError, _GifFrameError, _GifLzwError):
        pass
    return best
