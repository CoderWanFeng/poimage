"""Conservative bounded PNG chunk parser for native IDAT optimization."""

import struct
import zlib


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Ancillary chunk types defined by the PNG Third Edition. Unknown
# unsafe-to-copy ancillary chunks make the file ineligible for IDAT editing.
_KNOWN_ANCILLARY_CHUNKS = frozenset((
    b"tRNS", b"cHRM", b"gAMA", b"iCCP", b"sBIT", b"sRGB",
    b"cICP", b"mDCV", b"cLLI", b"tEXt", b"zTXt", b"iTXt",
    b"bKGD", b"hIST", b"pHYs", b"sPLT", b"eXIf", b"tIME",
))


class _PngFormatError(ValueError):
    pass


class _PngLimits:
    __slots__ = (
        "max_baseline_bytes", "max_chunks", "max_idat_chunks",
        "max_pixels", "max_inflated_bytes", "max_rows",
    )

    def __init__(
        self,
        max_baseline_bytes=16 * 1024 * 1024,
        max_chunks=1024,
        max_idat_chunks=256,
        max_pixels=16 * 1024 * 1024,
        max_inflated_bytes=16 * 1024 * 1024,
        max_rows=64 * 1024,
    ):
        self.max_baseline_bytes = max_baseline_bytes
        self.max_chunks = max_chunks
        self.max_idat_chunks = max_idat_chunks
        self.max_pixels = max_pixels
        self.max_inflated_bytes = max_inflated_bytes
        self.max_rows = max_rows


_DEFAULT_PNG_LIMITS = _PngLimits()


class _PngDocument:
    __slots__ = (
        "width", "height", "bit_depth", "color_type", "channels",
        "row_bytes", "filter_bytes_per_pixel", "idat_start", "idat_end",
        "idat_payload", "chunks",
    )

    def __init__(
        self, width, height, bit_depth, color_type, channels, row_bytes,
        filter_bytes_per_pixel, idat_start, idat_end, idat_payload, chunks,
    ):
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.color_type = color_type
        self.channels = channels
        self.row_bytes = row_bytes
        self.filter_bytes_per_pixel = filter_bytes_per_pixel
        self.idat_start = idat_start
        self.idat_end = idat_end
        self.idat_payload = idat_payload
        self.chunks = chunks


def _parse_png(data, limits=None):
    if limits is None:
        limits = _DEFAULT_PNG_LIMITS
    if len(data) > limits.max_baseline_bytes:
        raise _PngFormatError("PNG baseline limit exceeded")
    if not data.startswith(_PNG_SIGNATURE):
        raise _PngFormatError("invalid PNG signature")

    offset = len(_PNG_SIGNATURE)
    chunks = []
    idat_payloads = []
    idat_start = None
    idat_end = None
    idat_closed = False
    ihdr = None
    plte = None
    while offset < len(data):
        if len(chunks) >= limits.max_chunks or offset + 12 > len(data):
            raise _PngFormatError("invalid PNG chunk structure")
        start = offset
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise _PngFormatError("truncated PNG chunk")
        if not all(
            65 <= value <= 90 or 97 <= value <= 122
            for value in chunk_type
        ) or chunk_type[2] & 0x20:
            raise _PngFormatError("invalid PNG chunk type")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[end - 4:end])[0]
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise _PngFormatError("invalid PNG chunk CRC")
        chunks.append((chunk_type, start, end))

        if len(chunks) == 1:
            if chunk_type != b"IHDR" or length != 13:
                raise _PngFormatError("PNG IHDR must be first")
            ihdr = payload
        elif chunk_type == b"IHDR":
            raise _PngFormatError("duplicate PNG IHDR")

        if chunk_type in (b"acTL", b"fcTL", b"fdAT"):
            raise _PngFormatError("APNG is not eligible")
        if not chunk_type[0] & 0x20 and chunk_type not in (
            b"IHDR", b"PLTE", b"IDAT", b"IEND"
        ):
            raise _PngFormatError("unknown critical PNG chunk")
        if (
            chunk_type[0] & 0x20
            and not chunk_type[3] & 0x20
            and chunk_type not in _KNOWN_ANCILLARY_CHUNKS
        ):
            raise _PngFormatError("unknown unsafe-to-copy PNG chunk")
        if chunk_type == b"PLTE":
            if idat_start is not None or plte is not None:
                raise _PngFormatError("invalid PNG PLTE placement")
            plte = payload
        if chunk_type == b"IDAT":
            if idat_closed or len(idat_payloads) >= limits.max_idat_chunks:
                raise _PngFormatError("invalid PNG IDAT run")
            if idat_start is None:
                idat_start = start
            idat_end = end
            idat_payloads.append(payload)
        elif idat_start is not None and chunk_type != b"IEND":
            idat_closed = True
        if chunk_type == b"IEND":
            if length != 0 or end != len(data):
                raise _PngFormatError("invalid PNG IEND")
            break
        offset = end

    if not chunks or chunks[-1][0] != b"IEND" or idat_start is None:
        raise _PngFormatError("incomplete PNG")
    width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )
    if width <= 0 or height <= 0 or width * height > limits.max_pixels:
        raise _PngFormatError("PNG pixel limit exceeded")
    if height > limits.max_rows:
        raise _PngFormatError("PNG row limit exceeded")
    if compression != 0 or filtering != 0 or interlace != 0:
        raise _PngFormatError("unsupported PNG encoding method")
    valid_depths = {
        0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
        4: (8, 16), 6: (8, 16),
    }
    channels_by_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    if color_type not in valid_depths or bit_depth not in valid_depths[color_type]:
        raise _PngFormatError("invalid PNG color type or bit depth")
    palette_entries = None
    if plte is not None:
        if len(plte) == 0 or len(plte) % 3 or len(plte) // 3 > 256:
            raise _PngFormatError("invalid PNG palette")
        palette_entries = len(plte) // 3
    if color_type == 3:
        if plte is None or palette_entries > 1 << bit_depth:
            raise _PngFormatError("invalid indexed PNG palette")
    elif color_type in (0, 4) and plte is not None:
        raise _PngFormatError("invalid grayscale PNG palette")

    channels = channels_by_type[color_type]
    bits_per_pixel = channels * bit_depth
    row_bytes = (width * bits_per_pixel + 7) // 8
    expected = height * (row_bytes + 1)
    if expected > limits.max_inflated_bytes:
        raise _PngFormatError("PNG inflated data limit exceeded")
    return _PngDocument(
        width, height, bit_depth, color_type, channels, row_bytes,
        max(1, (bits_per_pixel + 7) // 8), idat_start, idat_end,
        b"".join(idat_payloads), chunks,
    )
