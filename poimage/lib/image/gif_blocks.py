"""Bounded GIF87a/GIF89a block scanner for native repacketization."""


class _GifFormatError(ValueError):
    """Reject a GIF that cannot be repacketized without ambiguity."""

    def __init__(self, offset: int, context: str):
        super().__init__("{} at byte {}".format(context, offset))
        self.offset = offset
        self.context = context


class _GifLimits:
    """Resource limits for the internal GIF scanner."""

    __slots__ = (
        "max_input_bytes",
        "max_blocks",
        "max_images",
        "max_sub_blocks",
        "max_extension_bytes",
    )

    def __init__(
        self,
        max_input_bytes=32 * 1024 * 1024,
        max_blocks=100000,
        max_images=10000,
        max_sub_blocks=250000,
        max_extension_bytes=16 * 1024 * 1024,
    ):
        self.max_input_bytes = max_input_bytes
        self.max_blocks = max_blocks
        self.max_images = max_images
        self.max_sub_blocks = max_sub_blocks
        self.max_extension_bytes = max_extension_bytes


_DEFAULT_GIF_LIMITS = _GifLimits()


class _ImageDataSpan:
    """Locate one image-data sub-block chain in the original file."""

    __slots__ = (
        "start",
        "end",
        "payload_length",
        "packet_count",
        "minimum_code_size_offset",
        "width",
        "height",
        "pixel_count",
    )

    def __init__(
        self,
        start,
        end,
        payload_length,
        packet_count,
        minimum_code_size_offset,
        width,
        height,
    ):
        self.start = start
        self.end = end
        self.payload_length = payload_length
        self.packet_count = packet_count
        self.minimum_code_size_offset = minimum_code_size_offset
        self.width = width
        self.height = height
        self.pixel_count = width * height


class _Cursor:
    __slots__ = ("data", "offset")

    def __init__(self, data):
        self.data = data
        self.offset = 0

    def read_byte(self, context):
        if self.offset >= len(self.data):
            raise _GifFormatError(self.offset, "truncated {}".format(context))
        value = self.data[self.offset]
        self.offset += 1
        return value

    def read_exact(self, count, context):
        end = self.offset + count
        if end > len(self.data):
            raise _GifFormatError(self.offset, "truncated {}".format(context))
        value = self.data[self.offset:end]
        self.offset = end
        return value


class _ScanState:
    __slots__ = (
        "limits",
        "blocks",
        "images",
        "sub_blocks",
        "extension_bytes",
    )

    def __init__(self, limits):
        self.limits = limits
        self.blocks = 0
        self.images = 0
        self.sub_blocks = 0
        self.extension_bytes = 0

    def add_block(self, offset):
        self.blocks += 1
        if self.blocks > self.limits.max_blocks:
            raise _GifFormatError(offset, "GIF block limit exceeded")

    def add_image(self, offset):
        self.images += 1
        if self.images > self.limits.max_images:
            raise _GifFormatError(offset, "GIF image limit exceeded")

    def add_sub_block(self, offset):
        self.sub_blocks += 1
        if self.sub_blocks > self.limits.max_sub_blocks:
            raise _GifFormatError(offset, "GIF sub-block limit exceeded")

    def add_extension_bytes(self, count, offset):
        self.extension_bytes += count
        if self.extension_bytes > self.limits.max_extension_bytes:
            raise _GifFormatError(offset, "GIF extension data limit exceeded")


def _color_table_size(packed):
    return 3 * (1 << ((packed & 0x07) + 1))


def _read_sub_blocks(cursor, state, extension_data):
    start = cursor.offset
    packet_count = 0
    payload_length = 0

    while True:
        length_offset = cursor.offset
        length = cursor.read_byte("sub-block length")
        if length == 0:
            break

        state.add_sub_block(length_offset)
        cursor.read_exact(length, "sub-block payload")
        packet_count += 1
        payload_length += length
        if extension_data:
            state.add_extension_bytes(length, length_offset)

    return start, cursor.offset, payload_length, packet_count


def _read_fixed_extension_header(cursor, state, expected_size, context):
    size_offset = cursor.offset
    size = cursor.read_byte("{} block size".format(context))
    if size != expected_size:
        raise _GifFormatError(size_offset, "invalid {} block size".format(context))
    state.add_sub_block(size_offset)
    cursor.read_exact(size, context)
    state.add_extension_bytes(size, size_offset)


def _read_extension(cursor, state):
    label_offset = cursor.offset
    label = cursor.read_byte("extension label")

    if label == 0xF9:
        _read_fixed_extension_header(
            cursor,
            state,
            4,
            "graphic control extension",
        )
        terminator_offset = cursor.offset
        if cursor.read_byte("graphic control terminator") != 0:
            raise _GifFormatError(
                terminator_offset,
                "invalid graphic control terminator",
            )
        return

    if label == 0x01:
        _read_fixed_extension_header(
            cursor,
            state,
            12,
            "plain text extension",
        )
        _read_sub_blocks(cursor, state, extension_data=True)
        return

    if label == 0xFF:
        _read_fixed_extension_header(
            cursor,
            state,
            11,
            "application extension",
        )
        _read_sub_blocks(cursor, state, extension_data=True)
        return

    _read_sub_blocks(cursor, state, extension_data=True)


def _iter_image_data_ranges(data, span):
    """Yield payload ranges from a previously validated image-data span."""
    offset = span.start
    while offset < span.end:
        length = data[offset]
        offset += 1
        if length == 0:
            return
        end = offset + length
        yield offset, end
        offset = end


def _scan_gif(data, limits=None):
    """Return image-data spans without retaining packet payload objects."""
    if limits is None:
        limits = _DEFAULT_GIF_LIMITS
    if len(data) > limits.max_input_bytes:
        raise _GifFormatError(0, "GIF input size limit exceeded")

    cursor = _Cursor(data)
    header = cursor.read_exact(6, "GIF header")
    if header not in (b"GIF87a", b"GIF89a"):
        raise _GifFormatError(0, "invalid GIF header")

    logical_screen = cursor.read_exact(7, "logical screen descriptor")
    if logical_screen[4] & 0x80:
        cursor.read_exact(
            _color_table_size(logical_screen[4]),
            "global color table",
        )

    state = _ScanState(limits)
    image_spans = []

    while cursor.offset < len(data):
        marker_offset = cursor.offset
        marker = cursor.read_byte("top-level block marker")
        if marker == 0x3B:
            if cursor.offset != len(data):
                raise _GifFormatError(cursor.offset, "data after GIF trailer")
            return image_spans

        state.add_block(marker_offset)
        if marker == 0x21:
            _read_extension(cursor, state)
            continue

        if marker == 0x2C:
            state.add_image(marker_offset)
            descriptor = cursor.read_exact(9, "image descriptor")
            width = descriptor[4] | (descriptor[5] << 8)
            height = descriptor[6] | (descriptor[7] << 8)
            if descriptor[8] & 0x80:
                cursor.read_exact(
                    _color_table_size(descriptor[8]),
                    "local color table",
                )

            minimum_code_size_offset = cursor.offset
            minimum_code_size = cursor.read_byte("LZW minimum code size")
            if not 2 <= minimum_code_size <= 8:
                raise _GifFormatError(
                    minimum_code_size_offset,
                    "invalid LZW minimum code size",
                )
            start, end, payload_length, packet_count = _read_sub_blocks(
                cursor,
                state,
                extension_data=False,
            )
            image_spans.append(
                _ImageDataSpan(
                    start,
                    end,
                    payload_length,
                    packet_count,
                    minimum_code_size_offset,
                    width,
                    height,
                )
            )
            continue

        raise _GifFormatError(marker_offset, "invalid top-level GIF marker")

    raise _GifFormatError(cursor.offset, "missing GIF trailer")
