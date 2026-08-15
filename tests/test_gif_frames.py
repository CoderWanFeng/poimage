"""Tests for conservative GIF frame parsing and composition."""

import unittest

from poimage.lib.image.gif_frames import (
    _GifFrameError,
    _frame_effective_palette,
    _iter_composited_rgb,
    _iter_transparent_disposal2_rgba,
    _parse_gif_document,
    _require_opaque_i2,
    _timeline_signature,
)
from poimage.lib.image.gif_lzw import _DEFAULT_LZW_LIMITS, _encode_lzw_indices


_PALETTE = (
    b"\x00\x00\x00"
    b"\xff\x00\x00"
    b"\x00\xff\x00"
    b"\x00\x00\xff"
)


def _packets(payload):
    return bytes((len(payload),)) + payload + b"\x00"


def _frame(
    indices,
    width,
    height,
    left=0,
    top=0,
    packed=0,
    control=None,
    local_palette=None,
):
    if local_palette is not None:
        packed |= 0x81
    descriptor = (
        b"\x2c"
        + left.to_bytes(2, "little")
        + top.to_bytes(2, "little")
        + width.to_bytes(2, "little")
        + height.to_bytes(2, "little")
        + bytes((packed,))
    )
    gce = b""
    if control is not None:
        disposal, transparent, delay = control
        flags = disposal << 2
        if transparent:
            flags |= 1
        gce = b"\x21\xf9\x04" + bytes((flags,)) + delay.to_bytes(2, "little") + b"\x00\x00"
    payload = _encode_lzw_indices(bytes(indices), 2)
    return gce + descriptor + (local_palette or b"") + b"\x02" + _packets(payload)


def _gif(frames, width=3, height=2, prefix=b""):
    logical = (
        width.to_bytes(2, "little")
        + height.to_bytes(2, "little")
        + b"\x81\x00\x00"
    )
    return b"GIF89a" + logical + _PALETTE + prefix + b"".join(frames) + b"\x3b"


class TestGifFrameDocument(unittest.TestCase):
    def test_parses_controls_extensions_and_frames(self):
        comment = b"\x21\xfe\x03abc\x00"
        application = b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
        data = _gif(
            [
                _frame([0, 0, 0, 0, 0, 0], 3, 2, control=(1, False, 7)),
                _frame([0, 1, 0, 0, 0, 0], 3, 2, control=(0, False, 11)),
            ],
            prefix=comment + application,
        )

        document = _parse_gif_document(data)

        self.assertEqual((3, 2), (document.width, document.height))
        self.assertEqual(_PALETTE, document.global_palette)
        self.assertEqual([comment, application], document.non_gce_extensions)
        self.assertEqual([(7, 1), (11, 0)], [item[:2] for item in _timeline_signature(document)])

    def test_composes_full_and_partial_rectangles(self):
        source = _gif(
            [
                _frame([0, 0, 0, 0, 0, 0], 3, 2, control=(1, False, 1)),
                _frame([0, 1, 0, 0, 0, 0], 3, 2, control=(1, False, 2)),
            ]
        )
        candidate = _gif(
            [
                _frame([0, 0, 0, 0, 0, 0], 3, 2, control=(1, False, 1)),
                _frame([1], 1, 1, left=1, control=(1, False, 2)),
            ]
        )

        source_frames = list(_iter_composited_rgb(source, _parse_gif_document(source), _DEFAULT_LZW_LIMITS, True))
        candidate_frames = list(_iter_composited_rgb(candidate, _parse_gif_document(candidate), _DEFAULT_LZW_LIMITS, False))

        self.assertEqual(source_frames, candidate_frames)

    def test_records_local_palette_and_effective_palette(self):
        data = _gif(
            [
                _frame([0] * 6, 3, 2, local_palette=_PALETTE),
                _frame([0] * 6, 3, 2),
            ]
        )

        document = _parse_gif_document(data)

        self.assertEqual(_PALETTE, document.frames[0].local_palette)
        self.assertEqual(
            _PALETTE,
            _frame_effective_palette(document, document.frames[0]),
        )
        self.assertIsNotNone(document.frames[0].local_palette_start)

    def test_composes_transparent_disposal2_rectangles(self):
        source = _gif(
            [
                _frame([1, 0, 0, 0, 0, 0], 3, 2, control=(2, True, 1)),
                _frame([0, 1, 0, 0, 0, 0], 3, 2, control=(2, True, 2)),
            ]
        )
        candidate = _gif(
            [
                _frame([1, 0, 0, 0, 0, 0], 3, 2, control=(2, True, 1)),
                _frame([1], 1, 1, left=1, control=(2, True, 2)),
            ]
        )

        self.assertEqual(
            list(_iter_transparent_disposal2_rgba(source, _parse_gif_document(source), _DEFAULT_LZW_LIMITS, True)),
            list(_iter_transparent_disposal2_rgba(candidate, _parse_gif_document(candidate), _DEFAULT_LZW_LIMITS, False)),
        )

    def test_rejects_unsafe_source_features(self):
        cases = (
            _gif([_frame([0] * 6, 3, 2), _frame([0] * 6, 3, 2)]),
            _gif([_frame([0] * 6, 3, 2, control=(1, False, 1)), _frame([0] * 6, 3, 2, control=(2, False, 1))]),
            _gif([_frame([0] * 6, 3, 2), _frame([0] * 6, 3, 2, control=(1, True, 1))]),
            _gif([_frame([0] * 6, 3, 2), _frame([0] * 6, 3, 2, packed=0x40)]),
            _gif([_frame([0] * 6, 3, 2), _frame([0, 0], 2, 1)]),
        )
        for data in cases:
            with self.subTest(length=len(data)):
                with self.assertRaises(_GifFrameError):
                    _require_opaque_i2(_parse_gif_document(data), True)

    def test_plain_text_and_unknown_extensions_are_ineligible(self):
        plain = b"\x21\x01\x0c" + bytes(range(12)) + b"\x00"
        unknown = b"\x21\xce\x01x\x00"
        frames = [_frame([0] * 6, 3, 2), _frame([0] * 6, 3, 2)]
        for extension in (plain, unknown):
            data = _gif(frames, prefix=extension)
            with self.subTest(extension=extension[:2]):
                with self.assertRaises(_GifFrameError):
                    _require_opaque_i2(_parse_gif_document(data), True)


if __name__ == "__main__":
    unittest.main()
