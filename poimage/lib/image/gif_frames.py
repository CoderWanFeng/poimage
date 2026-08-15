"""Bounded GIF frame metadata and opaque-frame composition."""

from poimage.lib.image.gif_blocks import (
    _GifFormatError,
    _iter_image_data_ranges,
    _scan_gif,
)
from poimage.lib.image.gif_lzw import (
    _GifLzwError,
    _GifLzwWork,
    _decode_lzw_indices,
)


class _GifFrameError(ValueError):
    """Reject a GIF that is not safe for conservative frame differencing."""


class _GraphicControl:
    __slots__ = ("start", "end", "raw", "disposal", "delay", "transparent", "transparent_index")

    def __init__(self, start, end, raw):
        self.start = start
        self.end = end
        self.raw = raw
        packed = raw[3]
        self.disposal = (packed >> 2) & 0x07
        self.delay = raw[4] | (raw[5] << 8)
        self.transparent = bool(packed & 0x01)
        self.transparent_index = raw[6]


class _GifFrame:
    __slots__ = (
        "span", "descriptor_offset", "left", "top", "width", "height",
        "packed", "has_local_table", "interlaced", "control",
        "local_palette", "local_palette_start", "local_palette_end",
    )

    def __init__(
        self,
        span,
        descriptor_offset,
        descriptor,
        control,
        local_palette,
        local_palette_start,
        local_palette_end,
    ):
        self.span = span
        self.descriptor_offset = descriptor_offset
        self.left = descriptor[0] | (descriptor[1] << 8)
        self.top = descriptor[2] | (descriptor[3] << 8)
        self.width = descriptor[4] | (descriptor[5] << 8)
        self.height = descriptor[6] | (descriptor[7] << 8)
        self.packed = descriptor[8]
        self.has_local_table = bool(self.packed & 0x80)
        self.interlaced = bool(self.packed & 0x40)
        self.control = control
        self.local_palette = local_palette
        self.local_palette_start = local_palette_start
        self.local_palette_end = local_palette_end


class _GifDocument:
    __slots__ = (
        "width", "height", "background_index", "global_palette", "frames",
        "non_gce_extensions", "unsupported_extensions", "ambiguous_control",
    )

    def __init__(self, width, height, background_index, global_palette):
        self.width = width
        self.height = height
        self.background_index = background_index
        self.global_palette = global_palette
        self.frames = []
        self.non_gce_extensions = []
        self.unsupported_extensions = False
        self.ambiguous_control = False


def _skip_sub_blocks(data, offset):
    while True:
        length = data[offset]
        offset += 1
        if length == 0:
            return offset
        offset += length


def _parse_gif_document(data, limits=None):
    spans = _scan_gif(data, limits=limits)
    logical = data[6:13]
    width = logical[0] | (logical[1] << 8)
    height = logical[2] | (logical[3] << 8)
    packed = logical[4]
    offset = 13
    palette = None
    if packed & 0x80:
        palette_size = 3 * (1 << ((packed & 0x07) + 1))
        palette = data[offset:offset + palette_size]
        offset += palette_size
    document = _GifDocument(width, height, logical[5], palette)
    pending_control = None
    span_index = 0

    while data[offset] != 0x3B:
        marker = data[offset]
        if marker == 0x21:
            start = offset
            label = data[offset + 1]
            if label == 0xF9:
                end = offset + 8
                control = _GraphicControl(start, end, data[start:end])
                if pending_control is not None:
                    document.ambiguous_control = True
                pending_control = control
                offset = end
                continue

            if label == 0x01:
                fixed_size = data[offset + 2]
                offset = _skip_sub_blocks(data, offset + 3 + fixed_size)
                document.unsupported_extensions = True
                pending_control = None
            elif label == 0xFF:
                fixed_size = data[offset + 2]
                offset = _skip_sub_blocks(data, offset + 3 + fixed_size)
            else:
                offset = _skip_sub_blocks(data, offset + 2)
                if label != 0xFE:
                    document.unsupported_extensions = True
            document.non_gce_extensions.append(data[start:offset])
            continue

        if marker != 0x2C or span_index >= len(spans):
            raise _GifFormatError(offset, "invalid GIF frame structure")
        descriptor_offset = offset
        descriptor = data[offset + 1:offset + 10]
        offset += 10
        local_palette = None
        local_palette_start = None
        local_palette_end = None
        if descriptor[8] & 0x80:
            local_palette_start = offset
            local_palette_end = offset + 3 * (
                1 << ((descriptor[8] & 0x07) + 1)
            )
            local_palette = data[local_palette_start:local_palette_end]
            offset = local_palette_end
        offset += 1
        span = spans[span_index]
        if offset != span.start:
            raise _GifFormatError(offset, "GIF image span mismatch")
        document.frames.append(
            _GifFrame(
                span,
                descriptor_offset,
                descriptor,
                pending_control,
                local_palette,
                local_palette_start,
                local_palette_end,
            )
        )
        pending_control = None
        span_index += 1
        offset = span.end

    if pending_control is not None:
        document.ambiguous_control = True
    return document


def _frame_disposal(frame):
    if frame.control is None:
        return 0
    return frame.control.disposal


def _require_opaque_i2(document, full_canvas):
    if len(document.frames) < 2:
        raise _GifFrameError("GIF has fewer than two frames")
    if document.width <= 0 or document.height <= 0:
        raise _GifFrameError("GIF logical screen has no pixels")
    if document.global_palette is None:
        raise _GifFrameError("GIF has no global color table")
    if document.unsupported_extensions or document.ambiguous_control:
        raise _GifFrameError("GIF extension semantics are not eligible")

    for frame in document.frames:
        if frame.has_local_table or frame.interlaced:
            raise _GifFrameError("GIF frame table or interlace is not eligible")
        if frame.control is not None and frame.control.transparent:
            raise _GifFrameError("transparent GIF frame is not eligible")
        if _frame_disposal(frame) != 1:
            raise _GifFrameError("GIF disposal method is not eligible")
        if (
            frame.left + frame.width > document.width
            or frame.top + frame.height > document.height
        ):
            raise _GifFrameError("GIF frame rectangle exceeds the canvas")
        if full_canvas and (
            frame.left != 0
            or frame.top != 0
            or frame.width != document.width
            or frame.height != document.height
        ):
            raise _GifFrameError("GIF source frame is not full canvas")


def _decode_frame_indices(data, frame, work):
    payload = b"".join(
        data[start:end]
        for start, end in _iter_image_data_ranges(data, frame.span)
    )
    return _decode_lzw_indices(
        payload,
        data[frame.span.minimum_code_size_offset],
        frame.width * frame.height,
        work=work,
    )


def _iter_composited_rgb(data, document, lzw_limits, full_canvas):
    _require_opaque_i2(document, full_canvas)
    canvas_pixels = document.width * document.height
    if canvas_pixels > lzw_limits.max_image_pixels:
        raise _GifFrameError("GIF canvas pixel limit exceeded")
    canvas = bytearray(canvas_pixels)
    work = _GifLzwWork(lzw_limits)
    palette = document.global_palette

    for frame in document.frames:
        indices = _decode_frame_indices(data, frame, work)
        for row in range(frame.height):
            source_start = row * frame.width
            target_start = (frame.top + row) * document.width + frame.left
            canvas[target_start:target_start + frame.width] = indices[
                source_start:source_start + frame.width
            ]

        rgb = bytearray(canvas_pixels * 3)
        for pixel, palette_index in enumerate(canvas):
            palette_offset = palette_index * 3
            if palette_offset + 3 > len(palette):
                raise _GifFrameError("GIF palette index is out of range")
            rgb_offset = pixel * 3
            rgb[rgb_offset:rgb_offset + 3] = palette[
                palette_offset:palette_offset + 3
            ]
        yield bytes(rgb)


def _frame_effective_palette(document, frame):
    palette = frame.local_palette or document.global_palette
    if palette is None:
        raise _GifFrameError("GIF frame has no color table")
    return palette


def _require_transparent_disposal2_i2(document, full_canvas):
    if len(document.frames) < 2 or document.global_palette is None:
        raise _GifFrameError("transparent GIF structure is not eligible")
    if document.unsupported_extensions or document.ambiguous_control:
        raise _GifFrameError("GIF extension semantics are not eligible")
    transparent_index = None
    for frame in document.frames:
        if frame.interlaced or frame.has_local_table:
            raise _GifFrameError("transparent GIF palette is not eligible")
        if frame.control is None or not frame.control.transparent:
            raise _GifFrameError("GIF frame has no transparency control")
        if frame.control.disposal != 2:
            raise _GifFrameError("transparent GIF disposal is not eligible")
        if transparent_index is None:
            transparent_index = frame.control.transparent_index
        elif frame.control.transparent_index != transparent_index:
            raise _GifFrameError("GIF transparent index changed")
        if (
            frame.left + frame.width > document.width
            or frame.top + frame.height > document.height
        ):
            raise _GifFrameError("GIF frame rectangle exceeds the canvas")
        if full_canvas and (
            frame.left != 0
            or frame.top != 0
            or frame.width != document.width
            or frame.height != document.height
        ):
            raise _GifFrameError("transparent GIF source is not full canvas")
    if document.background_index != transparent_index:
        raise _GifFrameError("GIF background is not the transparent index")


def _iter_transparent_disposal2_rgba(
    data,
    document,
    lzw_limits,
    full_canvas,
):
    _require_transparent_disposal2_i2(document, full_canvas)
    canvas_pixels = document.width * document.height
    if canvas_pixels > lzw_limits.max_image_pixels:
        raise _GifFrameError("GIF canvas pixel limit exceeded")
    if canvas_pixels * 12 > lzw_limits.max_candidate_bytes:
        raise _GifFrameError("GIF RGBA state limit exceeded")
    canvas = bytearray(canvas_pixels * 4)
    work = _GifLzwWork(lzw_limits)

    for frame in document.frames:
        indices = _decode_frame_indices(data, frame, work)
        palette = _frame_effective_palette(document, frame)
        transparent_index = frame.control.transparent_index
        for row in range(frame.height):
            for column in range(frame.width):
                index = indices[row * frame.width + column]
                if index == transparent_index:
                    continue
                palette_offset = index * 3
                if palette_offset + 3 > len(palette):
                    raise _GifFrameError("GIF palette index is out of range")
                canvas_offset = (
                    (frame.top + row) * document.width
                    + frame.left
                    + column
                ) * 4
                canvas[canvas_offset:canvas_offset + 3] = palette[
                    palette_offset:palette_offset + 3
                ]
                canvas[canvas_offset + 3] = 255
        displayed = bytes(canvas)
        for row in range(frame.top, frame.top + frame.height):
            start = (row * document.width + frame.left) * 4
            end = start + frame.width * 4
            canvas[start:end] = b"\x00" * (frame.width * 4)
        yield displayed, bytes(canvas)


def _timeline_signature(document):
    return [
        (
            frame.control.delay if frame.control is not None else 0,
            _frame_disposal(frame),
            frame.control.raw if frame.control is not None else None,
        )
        for frame in document.frames
    ]
