"""Bounded clean-room GIF LZW decoding and deterministic encoding."""


class _GifLzwError(ValueError):
    """Reject an LZW stream that cannot be recoded safely."""


class _GifLzwLimits:
    """Resource limits for native GIF LZW processing."""

    __slots__ = (
        "max_image_pixels",
        "max_total_pixels",
        "max_total_codes",
        "max_candidate_bytes",
    )

    def __init__(
        self,
        max_image_pixels=16 * 1024 * 1024,
        max_total_pixels=32 * 1024 * 1024,
        max_total_codes=32 * 1024 * 1024,
        max_candidate_bytes=32 * 1024 * 1024,
    ):
        self.max_image_pixels = max_image_pixels
        self.max_total_pixels = max_total_pixels
        self.max_total_codes = max_total_codes
        self.max_candidate_bytes = max_candidate_bytes


_DEFAULT_LZW_LIMITS = _GifLzwLimits()


class _GifLzwWork:
    __slots__ = ("limits", "total_pixels", "total_codes")

    def __init__(self, limits=None):
        self.limits = limits or _DEFAULT_LZW_LIMITS
        self.total_pixels = 0
        self.total_codes = 0

    def reserve_pixels(self, pixel_count):
        if pixel_count <= 0:
            raise _GifLzwError("GIF image has no pixels")
        if pixel_count > self.limits.max_image_pixels:
            raise _GifLzwError("GIF image pixel limit exceeded")
        self.total_pixels += pixel_count
        if self.total_pixels > self.limits.max_total_pixels:
            raise _GifLzwError("GIF total pixel limit exceeded")

    def add_code(self):
        self.total_codes += 1
        if self.total_codes > self.limits.max_total_codes:
            raise _GifLzwError("GIF LZW code limit exceeded")


class _LsbCodeReader:
    __slots__ = ("data", "bit_offset")

    def __init__(self, data):
        self.data = data
        self.bit_offset = 0

    def read(self, code_size):
        end_bit = self.bit_offset + code_size
        if end_bit > len(self.data) * 8:
            raise _GifLzwError("truncated GIF LZW code")

        byte_offset = self.bit_offset // 8
        bit_shift = self.bit_offset % 8
        byte_count = (bit_shift + code_size + 7) // 8
        packed = int.from_bytes(
            self.data[byte_offset:byte_offset + byte_count],
            "little",
        )
        self.bit_offset = end_bit
        return (packed >> bit_shift) & ((1 << code_size) - 1)


class _LsbCodeWriter:
    __slots__ = ("data", "bit_offset", "max_bytes")

    def __init__(self, max_bytes):
        self.data = bytearray()
        self.bit_offset = 0
        self.max_bytes = max_bytes

    def write(self, code, code_size):
        if code < 0 or code >= 1 << code_size:
            raise _GifLzwError("GIF LZW code does not fit its width")

        remaining = code_size
        value = code
        while remaining:
            byte_offset = self.bit_offset // 8
            bit_shift = self.bit_offset % 8
            if byte_offset == len(self.data):
                if len(self.data) >= self.max_bytes:
                    raise _GifLzwError("GIF LZW candidate limit exceeded")
                self.data.append(0)

            count = min(remaining, 8 - bit_shift)
            self.data[byte_offset] |= (value & ((1 << count) - 1)) << bit_shift
            value >>= count
            remaining -= count
            self.bit_offset += count

    def finish(self):
        return bytes(self.data)


def _validate_minimum_code_size(minimum_code_size):
    if not 2 <= minimum_code_size <= 8:
        raise _GifLzwError("invalid GIF LZW minimum code size")


def _reset_decoder_tables(prefix, suffix, clear_code):
    for code in range(clear_code):
        prefix[code] = -1
        suffix[code] = code


def _append_decoded_entry(
    output,
    code,
    clear_code,
    prefix,
    suffix,
    stack,
    expected_pixels,
):
    depth = 0
    current = code
    while current >= clear_code:
        if current >= 4096 or prefix[current] < 0 or depth >= 4095:
            raise _GifLzwError("invalid GIF LZW dictionary chain")
        stack[depth] = suffix[current]
        depth += 1
        current = prefix[current]

    if current < 0 or current >= clear_code:
        raise _GifLzwError("invalid GIF LZW literal")
    stack[depth] = current
    depth += 1
    first_byte = current

    if len(output) + depth > expected_pixels:
        raise _GifLzwError("GIF LZW stream has excess pixels")
    for index in range(depth - 1, -1, -1):
        output.append(stack[index])
    return first_byte


def _decode_lzw_indices(
    payload,
    minimum_code_size,
    expected_pixels,
    limits=None,
    work=None,
):
    """Decode one GIF image payload to its palette-index stream."""
    _validate_minimum_code_size(minimum_code_size)
    if limits is None:
        limits = _DEFAULT_LZW_LIMITS
    if work is None:
        work = _GifLzwWork(limits)
    work.reserve_pixels(expected_pixels)

    clear_code = 1 << minimum_code_size
    end_code = clear_code + 1
    first_dictionary_code = end_code + 1
    code_size = minimum_code_size + 1
    next_code = first_dictionary_code
    prefix = [-1] * 4096
    suffix = [0] * 4096
    stack = [0] * 4096
    _reset_decoder_tables(prefix, suffix, clear_code)

    reader = _LsbCodeReader(payload)
    work.add_code()
    if reader.read(code_size) != clear_code:
        raise _GifLzwError("GIF LZW stream does not start with CLEAR")

    output = bytearray()
    previous_code = None
    while True:
        work.add_code()
        code = reader.read(code_size)

        if code == clear_code:
            code_size = minimum_code_size + 1
            next_code = first_dictionary_code
            previous_code = None
            continue

        if code == end_code:
            if len(output) != expected_pixels:
                raise _GifLzwError("GIF LZW stream has an invalid pixel count")
            if len(payload) * 8 - reader.bit_offset >= 8:
                raise _GifLzwError("GIF LZW stream has data after EOI")
            return bytes(output)

        if code < next_code:
            first_byte = _append_decoded_entry(
                output,
                code,
                clear_code,
                prefix,
                suffix,
                stack,
                expected_pixels,
            )
        elif code == next_code and previous_code is not None:
            first_byte = _append_decoded_entry(
                output,
                previous_code,
                clear_code,
                prefix,
                suffix,
                stack,
                expected_pixels,
            )
            if len(output) >= expected_pixels:
                raise _GifLzwError("GIF LZW stream has excess pixels")
            output.append(first_byte)
        else:
            raise _GifLzwError("undefined GIF LZW code")

        if previous_code is not None and next_code < 4096:
            prefix[next_code] = previous_code
            suffix[next_code] = first_byte
            next_code += 1
            if next_code == 1 << code_size and code_size < 12:
                code_size += 1

        previous_code = code


def _encode_lzw_indices(indices, minimum_code_size, limits=None):
    """Encode palette indices as a deterministic GIF LZW payload."""
    _validate_minimum_code_size(minimum_code_size)
    if limits is None:
        limits = _DEFAULT_LZW_LIMITS
    if not indices:
        raise _GifLzwError("GIF image has no pixels")
    if len(indices) > limits.max_image_pixels:
        raise _GifLzwError("GIF image pixel limit exceeded")

    clear_code = 1 << minimum_code_size
    end_code = clear_code + 1
    first_dictionary_code = end_code + 1
    for value in indices:
        if value >= clear_code:
            raise _GifLzwError("palette index exceeds GIF literal range")

    writer = _LsbCodeWriter(limits.max_candidate_bytes)
    code_size = minimum_code_size + 1
    next_code = first_dictionary_code
    dictionary = {}
    writer.write(clear_code, code_size)

    current = indices[0]
    for value in indices[1:]:
        key = (current, value)
        existing = dictionary.get(key)
        if existing is not None:
            current = existing
            continue

        writer.write(current, code_size)
        if next_code < 4096:
            dictionary[key] = next_code
            next_code += 1
            if next_code > 1 << code_size and code_size < 12:
                code_size += 1
        else:
            writer.write(clear_code, code_size)
            dictionary.clear()
            code_size = minimum_code_size + 1
            next_code = first_dictionary_code
        current = value

    writer.write(current, code_size)
    if next_code == 1 << code_size and code_size < 12:
        code_size += 1
    writer.write(end_code, code_size)
    return writer.finish()
