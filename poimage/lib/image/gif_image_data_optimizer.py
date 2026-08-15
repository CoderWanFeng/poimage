"""GIF image-data packet and LZW optimization stages."""

from poimage.lib.image.gif_blocks import (
    _iter_image_data_ranges,
    _scan_gif,
)
from poimage.lib.image.gif_lzw import (
    _GifLzwError,
    _GifLzwWork,
    _decode_lzw_indices,
    _encode_lzw_indices,
)


def _optimal_packet_count(payload_length):
    if payload_length == 0:
        return 0
    return (payload_length + 254) // 255


def _append_repacketized_image_data(result, data, span):
    remaining_payload = span.payload_length
    remaining_packet = 0
    for start, end in _iter_image_data_ranges(data, span):
        offset = start
        while offset < end:
            if remaining_packet == 0:
                remaining_packet = min(255, remaining_payload)
                result.append(remaining_packet)
            count = min(remaining_packet, end - offset)
            result.extend(data[offset:offset + count])
            offset += count
            remaining_packet -= count
            remaining_payload -= count
    result.append(0)


def _append_packetized_payload(result, payload):
    for offset in range(0, len(payload), 255):
        packet = payload[offset:offset + 255]
        result.append(len(packet))
        result.extend(packet)
    result.append(0)


def _collect_image_payload(data, span):
    return b"".join(
        data[start:end]
        for start, end in _iter_image_data_ranges(data, span)
    )


def _build_i0_candidate(data, image_spans):
    has_savings = any(
        span.packet_count > _optimal_packet_count(span.payload_length)
        for span in image_spans
    )
    if not has_savings:
        return None
    result = bytearray()
    previous_end = 0
    for span in image_spans:
        result.extend(data[previous_end:span.start])
        if span.packet_count > _optimal_packet_count(span.payload_length):
            _append_repacketized_image_data(result, data, span)
        else:
            result.extend(data[span.start:span.end])
        previous_end = span.end
    result.extend(data[previous_end:])
    if len(result) >= len(data):
        return None
    return bytes(result)


def _build_i1_candidate(data, image_spans, lzw_limits):
    total_pixels = 0
    for span in image_spans:
        if span.pixel_count <= 0:
            raise _GifLzwError("GIF image has no pixels")
        if span.pixel_count > lzw_limits.max_image_pixels:
            raise _GifLzwError("GIF image pixel limit exceeded")
        total_pixels += span.pixel_count
        if total_pixels > lzw_limits.max_total_pixels:
            raise _GifLzwError("GIF total pixel limit exceeded")
    result = bytearray()
    previous_end = 0
    source_work = _GifLzwWork(lzw_limits)
    for span in image_spans:
        result.extend(data[previous_end:span.start])
        if len(result) > lzw_limits.max_candidate_bytes:
            raise _GifLzwError("GIF LZW candidate limit exceeded")
        minimum_code_size = data[span.minimum_code_size_offset]
        indices = _decode_lzw_indices(
            _collect_image_payload(data, span),
            minimum_code_size,
            span.pixel_count,
            work=source_work,
        )
        recoded = _encode_lzw_indices(
            indices,
            minimum_code_size,
            limits=lzw_limits,
        )
        _append_packetized_payload(result, recoded)
        if len(result) > lzw_limits.max_candidate_bytes:
            raise _GifLzwError("GIF LZW candidate limit exceeded")
        previous_end = span.end
    result.extend(data[previous_end:])
    if len(result) > lzw_limits.max_candidate_bytes:
        raise _GifLzwError("GIF LZW candidate limit exceeded")
    return bytes(result)


def _validate_i1_candidate(
    source,
    candidate,
    source_spans,
    structural_limits,
    lzw_limits,
):
    candidate_spans = _scan_gif(candidate, limits=structural_limits)
    if len(candidate_spans) != len(source_spans):
        raise _GifLzwError("GIF image count changed")
    source_previous = 0
    candidate_previous = 0
    source_work = _GifLzwWork(lzw_limits)
    candidate_work = _GifLzwWork(lzw_limits)
    for source_span, candidate_span in zip(source_spans, candidate_spans):
        if (
            source[source_previous:source_span.start]
            != candidate[candidate_previous:candidate_span.start]
        ):
            raise _GifLzwError("GIF bytes outside image data changed")
        if (
            source_span.width != candidate_span.width
            or source_span.height != candidate_span.height
        ):
            raise _GifLzwError("GIF image dimensions changed")
        source_minimum = source[source_span.minimum_code_size_offset]
        candidate_minimum = candidate[candidate_span.minimum_code_size_offset]
        if source_minimum != candidate_minimum:
            raise _GifLzwError("GIF LZW minimum code size changed")
        source_indices = _decode_lzw_indices(
            _collect_image_payload(source, source_span),
            source_minimum,
            source_span.pixel_count,
            work=source_work,
        )
        candidate_indices = _decode_lzw_indices(
            _collect_image_payload(candidate, candidate_span),
            candidate_minimum,
            candidate_span.pixel_count,
            work=candidate_work,
        )
        if source_indices != candidate_indices:
            raise _GifLzwError("GIF palette-index stream changed")
        source_previous = source_span.end
        candidate_previous = candidate_span.end
    if source[source_previous:] != candidate[candidate_previous:]:
        raise _GifLzwError("GIF bytes outside image data changed")
