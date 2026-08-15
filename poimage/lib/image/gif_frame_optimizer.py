"""GIF frame geometry, palette, and playback optimization stages."""

from poimage.lib.image.gif_frames import (
    _GifFrameError,
    _decode_frame_indices,
    _frame_effective_palette,
    _iter_composited_rgb,
    _iter_transparent_disposal2_rgba,
    _parse_gif_document,
    _require_opaque_i2,
    _require_transparent_disposal2_i2,
    _timeline_signature,
)
from poimage.lib.image.gif_image_data_optimizer import (
    _append_packetized_payload,
    _collect_image_payload,
)
from poimage.lib.image.gif_lzw import (
    _GifLzwWork,
    _encode_lzw_indices,
)


def _palette_color(palette, index):
    offset = index * 3
    if offset + 3 > len(palette):
        raise _GifFrameError("GIF palette index is out of range")
    return palette[offset:offset + 3]


def _changed_rectangle(previous, current, palette, width, height):
    left = width
    top = height
    right = -1
    bottom = -1
    for offset, (before, after) in enumerate(zip(previous, current)):
        if _palette_color(palette, before) == _palette_color(palette, after):
            continue
        x = offset % width
        y = offset // width
        left = min(left, x)
        top = min(top, y)
        right = max(right, x)
        bottom = max(bottom, y)
    if right < 0:
        return 0, 0, 1, 1
    return left, top, right - left + 1, bottom - top + 1


def _crop_indices(indices, canvas_width, left, top, width, height):
    cropped = bytearray()
    for row in range(top, top + height):
        start = row * canvas_width + left
        cropped.extend(indices[start:start + width])
    return bytes(cropped)


def _build_i2_candidate(data, document, lzw_limits):
    _require_opaque_i2(document, True)
    total_pixels = sum(frame.width * frame.height for frame in document.frames)
    if total_pixels > lzw_limits.max_total_pixels:
        raise _GifFrameError("GIF total pixel limit exceeded")
    result = bytearray()
    previous_end = 0
    previous_indices = None
    work = _GifLzwWork(lzw_limits)
    for index, frame in enumerate(document.frames):
        indices = _decode_frame_indices(data, frame, work)
        if index == 0:
            left, top, width, height = 0, 0, frame.width, frame.height
        else:
            left, top, width, height = _changed_rectangle(
                previous_indices,
                indices,
                document.global_palette,
                document.width,
                document.height,
            )
        cropped = _crop_indices(
            indices,
            document.width,
            left,
            top,
            width,
            height,
        )
        result.extend(data[previous_end:frame.descriptor_offset])
        descriptor = bytearray(
            data[frame.descriptor_offset + 1:frame.descriptor_offset + 10]
        )
        descriptor[0:2] = left.to_bytes(2, "little")
        descriptor[2:4] = top.to_bytes(2, "little")
        descriptor[4:6] = width.to_bytes(2, "little")
        descriptor[6:8] = height.to_bytes(2, "little")
        result.append(0x2C)
        result.extend(descriptor)
        result.extend(data[frame.descriptor_offset + 10:frame.span.start])
        recoded = _encode_lzw_indices(
            cropped,
            data[frame.span.minimum_code_size_offset],
            limits=lzw_limits,
        )
        _append_packetized_payload(result, recoded)
        if len(result) > lzw_limits.max_candidate_bytes:
            raise _GifFrameError("GIF I2 candidate limit exceeded")
        previous_end = frame.span.end
        previous_indices = indices
    result.extend(data[previous_end:])
    if len(result) > lzw_limits.max_candidate_bytes:
        raise _GifFrameError("GIF I2 candidate limit exceeded")
    return bytes(result)


def _validate_i2_candidate(source, candidate, limits, lzw_limits):
    source_document = _parse_gif_document(source, limits=limits)
    candidate_document = _parse_gif_document(candidate, limits=limits)
    _require_opaque_i2(source_document, True)
    _require_opaque_i2(candidate_document, False)
    if (
        source_document.width != candidate_document.width
        or source_document.height != candidate_document.height
        or source_document.global_palette != candidate_document.global_palette
        or source_document.non_gce_extensions
        != candidate_document.non_gce_extensions
        or _timeline_signature(source_document)
        != _timeline_signature(candidate_document)
    ):
        raise _GifFrameError("GIF I2 metadata changed")

    source_frames = _iter_composited_rgb(
        source, source_document, lzw_limits, True
    )
    candidate_frames = _iter_composited_rgb(
        candidate, candidate_document, lzw_limits, False
    )
    for source_rgb, candidate_rgb in zip(source_frames, candidate_frames):
        if source_rgb != candidate_rgb:
            raise _GifFrameError("GIF I2 composed playback changed")

def _build_palette_dedup_candidate(data, document):
    if document.global_palette is None:
        return None
    result = bytearray()
    previous = 0
    removed = False
    for frame in document.frames:
        if (
            frame.local_palette is None
            or frame.local_palette != document.global_palette
        ):
            continue
        packed_offset = frame.descriptor_offset + 9
        result.extend(data[previous:packed_offset])
        result.append(data[packed_offset] & 0x7F)
        previous = frame.local_palette_end
        removed = True
    if not removed:
        return None
    result.extend(data[previous:])
    return bytes(result)



def _transparent_bounds(indices, transparent_index, width, height):
    positions = [
        offset
        for offset, value in enumerate(indices)
        if value != transparent_index
    ]
    if not positions:
        return 0, 0, 1, 1
    left = min(offset % width for offset in positions)
    right = max(offset % width for offset in positions)
    top = min(offset // width for offset in positions)
    bottom = max(offset // width for offset in positions)
    return left, top, right - left + 1, bottom - top + 1


def _build_transparent_i2_candidate(data, document, lzw_limits):
    _require_transparent_disposal2_i2(document, True)
    total_pixels = sum(frame.width * frame.height for frame in document.frames)
    if total_pixels > lzw_limits.max_total_pixels:
        raise _GifFrameError("GIF total pixel limit exceeded")
    result = bytearray()
    previous_end = 0
    work = _GifLzwWork(lzw_limits)
    for index, frame in enumerate(document.frames):
        indices = _decode_frame_indices(data, frame, work)
        transparent_index = frame.control.transparent_index
        if index == 0:
            left, top, width, height = 0, 0, frame.width, frame.height
        else:
            left, top, width, height = _transparent_bounds(
                indices,
                transparent_index,
                frame.width,
                frame.height,
            )
        cropped = _crop_indices(
            indices,
            document.width,
            left,
            top,
            width,
            height,
        )
        result.extend(data[previous_end:frame.descriptor_offset])
        descriptor = bytearray(
            data[frame.descriptor_offset + 1:frame.descriptor_offset + 10]
        )
        descriptor[0:2] = left.to_bytes(2, "little")
        descriptor[2:4] = top.to_bytes(2, "little")
        descriptor[4:6] = width.to_bytes(2, "little")
        descriptor[6:8] = height.to_bytes(2, "little")
        result.append(0x2C)
        result.extend(descriptor)
        result.extend(data[frame.descriptor_offset + 10:frame.span.start])
        recoded = _encode_lzw_indices(
            cropped,
            data[frame.span.minimum_code_size_offset],
            limits=lzw_limits,
        )
        _append_packetized_payload(result, recoded)
        if len(result) > lzw_limits.max_candidate_bytes:
            raise _GifFrameError("GIF transparent candidate limit exceeded")
        previous_end = frame.span.end
    result.extend(data[previous_end:])
    if len(result) > lzw_limits.max_candidate_bytes:
        raise _GifFrameError("GIF transparent candidate limit exceeded")
    return bytes(result)


def _palette_compaction_plan(data, document, lzw_limits):
    _require_transparent_disposal2_i2(document, False)
    used = {document.background_index}
    decoded_frames = []
    work = _GifLzwWork(lzw_limits)
    for frame in document.frames:
        indices = _decode_frame_indices(data, frame, work)
        decoded_frames.append(indices)
        used.update(indices)
        used.add(frame.control.transparent_index)
    ordered = sorted(used)
    mapping = {old: new for new, old in enumerate(ordered)}
    table_size = 2
    while table_size < len(ordered):
        table_size *= 2
    return mapping, table_size, decoded_frames


def _build_palette_compaction_candidate(data, document, lzw_limits):
    mapping, table_size, decoded_frames = _palette_compaction_plan(
        data,
        document,
        lzw_limits,
    )
    if table_size * 3 >= len(document.global_palette):
        return None, None

    new_palette = bytearray()
    for old_index in sorted(mapping):
        new_palette.extend(_palette_color(document.global_palette, old_index))
    new_palette.extend(b"\x00" * (table_size * 3 - len(new_palette)))
    minimum_code_size = max(2, table_size.bit_length() - 1)

    result = bytearray(data[:10])
    result.append((data[10] & 0xF8) | (table_size.bit_length() - 2))
    result.append(mapping[document.background_index])
    result.extend(data[12:13])
    result.extend(new_palette)
    previous = 13 + len(document.global_palette)

    for frame, indices in zip(document.frames, decoded_frames):
        transparent_offset = frame.control.start + 6
        result.extend(data[previous:transparent_offset])
        result.append(mapping[frame.control.transparent_index])
        result.extend(
            data[
                transparent_offset + 1:frame.span.minimum_code_size_offset
            ]
        )
        result.append(minimum_code_size)
        mapped = bytes(mapping[value] for value in indices)
        recoded = _encode_lzw_indices(
            mapped,
            minimum_code_size,
            limits=lzw_limits,
        )
        _append_packetized_payload(result, recoded)
        if len(result) > lzw_limits.max_candidate_bytes:
            raise _GifFrameError("GIF palette candidate limit exceeded")
        previous = frame.span.end
    result.extend(data[previous:])
    if len(result) > lzw_limits.max_candidate_bytes:
        raise _GifFrameError("GIF palette candidate limit exceeded")
    return bytes(result), mapping


def _validate_palette_compaction(
    source,
    candidate,
    mapping,
    limits,
    lzw_limits,
):
    source_document = _parse_gif_document(source, limits=limits)
    candidate_document = _parse_gif_document(candidate, limits=limits)
    _require_transparent_disposal2_i2(source_document, False)
    _require_transparent_disposal2_i2(candidate_document, False)
    if (
        source[:10] != candidate[:10]
        or source[12] != candidate[12]
        or source_document.width != candidate_document.width
        or source_document.height != candidate_document.height
        or source_document.non_gce_extensions
        != candidate_document.non_gce_extensions
        or len(source_document.frames) != len(candidate_document.frames)
        or (source[10] & 0xF8) != (candidate[10] & 0xF8)
        or candidate_document.background_index
        != mapping[source_document.background_index]
    ):
        raise _GifFrameError("GIF palette compaction metadata changed")

    for old_index, new_index in mapping.items():
        if _palette_color(
            source_document.global_palette,
            old_index,
        ) != _palette_color(candidate_document.global_palette, new_index):
            raise _GifFrameError("GIF palette color changed")

    expected_minimum = max(
        2,
        (len(candidate_document.global_palette) // 3).bit_length() - 1,
    )
    source_work = _GifLzwWork(lzw_limits)
    candidate_work = _GifLzwWork(lzw_limits)
    for source_frame, candidate_frame in zip(
        source_document.frames,
        candidate_document.frames,
    ):
        if (
            source_frame.left != candidate_frame.left
            or source_frame.top != candidate_frame.top
            or source_frame.width != candidate_frame.width
            or source_frame.height != candidate_frame.height
            or source_frame.packed != candidate_frame.packed
            or source_frame.control.delay != candidate_frame.control.delay
            or source_frame.control.disposal != candidate_frame.control.disposal
            or source_frame.control.raw[:6]
            != candidate_frame.control.raw[:6]
            or source_frame.control.raw[7:]
            != candidate_frame.control.raw[7:]
            or candidate[
                candidate_frame.span.minimum_code_size_offset
            ] != expected_minimum
            or candidate_frame.control.transparent_index
            != mapping[source_frame.control.transparent_index]
        ):
            raise _GifFrameError("GIF palette frame metadata changed")
        source_indices = _decode_frame_indices(
            source,
            source_frame,
            source_work,
        )
        candidate_indices = _decode_frame_indices(
            candidate,
            candidate_frame,
            candidate_work,
        )
        if candidate_indices != bytes(
            mapping[value] for value in source_indices
        ):
            raise _GifFrameError("GIF palette index mapping changed")

    source_states = _iter_transparent_disposal2_rgba(
        source,
        source_document,
        lzw_limits,
        False,
    )
    candidate_states = _iter_transparent_disposal2_rgba(
        candidate,
        candidate_document,
        lzw_limits,
        False,
    )
    for source_state, candidate_state in zip(
        source_states,
        candidate_states,
    ):
        if source_state != candidate_state:
            raise _GifFrameError("GIF palette playback changed")


def _validate_transparent_i2(source, candidate, limits, lzw_limits):
    source_document = _parse_gif_document(source, limits=limits)
    candidate_document = _parse_gif_document(candidate, limits=limits)
    _require_transparent_disposal2_i2(source_document, True)
    _require_transparent_disposal2_i2(candidate_document, False)
    if (
        source_document.global_palette != candidate_document.global_palette
        or source_document.non_gce_extensions
        != candidate_document.non_gce_extensions
        or _timeline_signature(source_document)
        != _timeline_signature(candidate_document)
    ):
        raise _GifFrameError("GIF transparent metadata changed")
    source_states = _iter_transparent_disposal2_rgba(
        source, source_document, lzw_limits, True
    )
    candidate_states = _iter_transparent_disposal2_rgba(
        candidate, candidate_document, lzw_limits, False
    )
    for source_state, candidate_state in zip(source_states, candidate_states):
        if source_state != candidate_state:
            raise _GifFrameError("GIF transparent playback changed")
