"""PNG scanline filter decoding and bounded candidate generation."""

import zlib

from poimage.lib.image.png_chunks import _PngFormatError


def _paeth(left, above, upper_left):
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def _inflate_scanlines(document):
    expected = document.height * (document.row_bytes + 1)
    decompressor = zlib.decompressobj(zlib.MAX_WBITS)
    inflated = decompressor.decompress(document.idat_payload, expected + 1)
    if (
        len(inflated) != expected
        or not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
    ):
        raise _PngFormatError("invalid PNG zlib stream")
    return inflated


def _inflate_rows(document):
    inflated = _inflate_scanlines(document)
    rows = []
    filters = []
    previous = bytes(document.row_bytes)
    offset = 0
    for _ in range(document.height):
        filter_type = inflated[offset]
        if filter_type > 4:
            raise _PngFormatError("invalid PNG row filter")
        filtered = inflated[offset + 1:offset + 1 + document.row_bytes]
        raw = _inverse_filter(
            filtered,
            previous,
            document.filter_bytes_per_pixel,
            filter_type,
        )
        rows.append(raw)
        filters.append(filter_type)
        previous = raw
        offset += document.row_bytes + 1
    return rows, filters


def _inverse_filter(filtered, previous, bpp, filter_type):
    if filter_type == 0:
        return bytes(filtered)

    raw = bytearray(len(filtered))
    for index, value in enumerate(filtered):
        left = raw[index - bpp] if index >= bpp else 0
        above = previous[index]
        upper_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = above
        elif filter_type == 3:
            predictor = (left + above) // 2
        else:
            predictor = _paeth(left, above, upper_left)
        raw[index] = (value + predictor) & 0xFF
    return bytes(raw)


def _forward_filter(raw, previous, bpp, filter_type):
    if filter_type == 0:
        return bytes(raw)

    filtered = bytearray(len(raw))
    for index, value in enumerate(raw):
        left = raw[index - bpp] if index >= bpp else 0
        above = previous[index]
        upper_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = above
        elif filter_type == 3:
            predictor = (left + above) // 2
        else:
            predictor = _paeth(left, above, upper_left)
        filtered[index] = (value - predictor) & 0xFF
    return bytes(filtered)


def _residual_score(filtered):
    return sum(value if value < 128 else 256 - value for value in filtered)


def _bigram_score(filtered):
    frequencies = {}
    previous = 256
    for value in filtered:
        pair = (previous << 8) | value
        frequencies[pair] = frequencies.get(pair, 0) + 1
        previous = value
    return (
        len(frequencies),
        -sum(count * count for count in frequencies.values()),
    )


def _encode_rows(rows, bpp, filter_plan):
    result = bytearray()
    previous = bytes(len(rows[0])) if rows else b""
    for row, filter_type in zip(rows, filter_plan):
        result.append(filter_type)
        result.extend(_forward_filter(row, previous, bpp, filter_type))
        previous = row
    return bytes(result)


def _adaptive_plans(rows, bpp):
    residual_plan = []
    bigram_plan = []
    previous = bytes(len(rows[0])) if rows else b""
    for row in rows:
        residual_best = None
        bigram_best = None
        for filter_type in range(5):
            filtered = _forward_filter(row, previous, bpp, filter_type)
            residual = _residual_score(filtered)
            bigram = _bigram_score(filtered)
            if residual_best is None or residual < residual_best[0]:
                residual_best = (residual, filter_type)
            if bigram_best is None or bigram < bigram_best[0]:
                bigram_best = (bigram, filter_type)
        residual_plan.append(residual_best[1])
        bigram_plan.append(bigram_best[1])
        previous = row
    return tuple(residual_plan), tuple(bigram_plan)


def _filter_plans(rows, bpp, original_filters):
    adaptive_residual, adaptive_bigram = _adaptive_plans(rows, bpp)
    candidates = (
        tuple(original_filters),
        tuple([0] * len(rows)),
        tuple([1] * len(rows)),
        tuple([4] * len(rows)),
        adaptive_residual,
        adaptive_bigram,
    )
    unique = []
    seen = set()
    for plan in candidates:
        if plan not in seen:
            unique.append(plan)
            seen.add(plan)
    return unique
