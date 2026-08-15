"""Specification-level tests for native GIF LZW processing."""

import random
import unittest

from poimage.lib.image.gif_lzw import (
    _GifLzwError,
    _GifLzwLimits,
    _GifLzwWork,
    _decode_lzw_indices,
    _encode_lzw_indices,
)


def _pack_codes(codes, minimum_code_size):
    clear_code = 1 << minimum_code_size
    end_code = clear_code + 1
    next_code = end_code + 1
    code_size = minimum_code_size + 1
    previous = False
    accumulator = 0
    bit_count = 0
    output = bytearray()

    for code in codes:
        accumulator |= code << bit_count
        bit_count += code_size
        while bit_count >= 8:
            output.append(accumulator & 0xFF)
            accumulator >>= 8
            bit_count -= 8

        if code == clear_code:
            next_code = end_code + 1
            code_size = minimum_code_size + 1
            previous = False
        elif code != end_code:
            if previous and next_code < 4096:
                next_code += 1
                if next_code == 1 << code_size and code_size < 12:
                    code_size += 1
            previous = True

    if bit_count:
        output.append(accumulator & 0xFF)
    return bytes(output)


def _unpack_codes(payload, minimum_code_size):
    clear_code = 1 << minimum_code_size
    end_code = clear_code + 1
    next_code = end_code + 1
    code_size = minimum_code_size + 1
    previous = False
    bit_offset = 0
    codes = []

    while bit_offset + code_size <= len(payload) * 8:
        byte_offset = bit_offset // 8
        bit_shift = bit_offset % 8
        byte_count = (bit_shift + code_size + 7) // 8
        packed = int.from_bytes(
            payload[byte_offset:byte_offset + byte_count],
            "little",
        )
        code = (packed >> bit_shift) & ((1 << code_size) - 1)
        bit_offset += code_size
        codes.append(code)

        if code == clear_code:
            next_code = end_code + 1
            code_size = minimum_code_size + 1
            previous = False
        elif code == end_code:
            return codes
        else:
            if previous and next_code < 4096:
                next_code += 1
                if next_code == 1 << code_size and code_size < 12:
                    code_size += 1
            previous = True

    return codes


class TestGifLzwDecoder(unittest.TestCase):
    def test_decodes_explicit_lsb_first_vector(self):
        payload = b"\x44\x0a"

        indices = _decode_lzw_indices(payload, 2, 2)

        self.assertEqual(b"\x00\x01", indices)
        self.assertEqual(payload, _pack_codes([4, 0, 1, 5], 2))

    def test_decodes_minimum_code_size_eight(self):
        payload = _pack_codes([256, 0, 127, 255, 257], 8)

        indices = _decode_lzw_indices(payload, 8, 3)

        self.assertEqual(bytes((0, 127, 255)), indices)

    def test_accepts_consecutive_and_midstream_clear(self):
        payload = _pack_codes([4, 4, 0, 4, 1, 5], 2)

        self.assertEqual(
            b"\x00\x01",
            _decode_lzw_indices(payload, 2, 2),
        )

    def test_decodes_kwkwk_entry(self):
        payload = b"\x84\x0b"

        indices = _decode_lzw_indices(payload, 2, 3)

        self.assertEqual(b"\x00\x00\x00", indices)
        self.assertEqual(payload, _pack_codes([4, 0, 6, 5], 2))

    def test_crosses_every_code_width_and_fills_dictionary(self):
        literal_count = 5000
        payload = _pack_codes(
            [4] + [0] * literal_count + [5],
            2,
        )

        indices = _decode_lzw_indices(payload, 2, literal_count)

        self.assertEqual(b"\x00" * literal_count, indices)

    def test_rejects_invalid_streams(self):
        cases = (
            (_pack_codes([0, 5], 2), 1, "start"),
            (_pack_codes([4, 7], 2), 1, "undefined"),
            (_pack_codes([4, 5], 2), 1, "pixel count"),
            (_pack_codes([4, 0, 1, 5], 2), 1, "excess"),
            (_pack_codes([4, 0], 2), 1, "truncated"),
            (_pack_codes([4, 0, 5], 2) + b"garbage", 1, "after EOI"),
        )
        for payload, pixels, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(_GifLzwError, message):
                    _decode_lzw_indices(payload, 2, pixels)

    def test_rejects_resource_limit_excess(self):
        payload = _pack_codes([4, 0, 1, 5], 2)
        limits = _GifLzwLimits(
            max_image_pixels=1,
            max_total_pixels=1,
            max_total_codes=2,
        )

        with self.assertRaisesRegex(_GifLzwError, "pixel limit"):
            _decode_lzw_indices(payload, 2, 2, limits=limits)

        work = _GifLzwWork(
            _GifLzwLimits(
                max_image_pixels=2,
                max_total_pixels=2,
                max_total_codes=2,
            )
        )
        with self.assertRaisesRegex(_GifLzwError, "code limit"):
            _decode_lzw_indices(payload, 2, 2, work=work)


class TestGifLzwEncoder(unittest.TestCase):
    def test_encodes_explicit_lsb_first_vector(self):
        self.assertEqual(
            b"\x44\x0a",
            _encode_lzw_indices(b"\x00\x01", 2),
        )

    def test_round_trips_deterministic_patterns(self):
        randomizer = random.Random(20260815)
        cases = (
            (b"\x00" * 10000, 2),
            (bytes((index % 2 for index in range(10000))), 2),
            (bytes(range(256)) * 20, 8),
            (bytes(randomizer.randrange(256) for _ in range(50000)), 8),
        )
        for indices, minimum_code_size in cases:
            with self.subTest(
                length=len(indices),
                minimum_code_size=minimum_code_size,
            ):
                first = _encode_lzw_indices(indices, minimum_code_size)
                second = _encode_lzw_indices(indices, minimum_code_size)
                self.assertEqual(first, second)
                self.assertEqual(
                    indices,
                    _decode_lzw_indices(
                        first,
                        minimum_code_size,
                        len(indices),
                    ),
                )

    def test_eoi_uses_width_after_final_decoder_addition(self):
        for length in range(1, 129):
            with self.subTest(length=length):
                indices = b"\x00" * length
                payload = _encode_lzw_indices(indices, 2)
                self.assertEqual(
                    indices,
                    _decode_lzw_indices(payload, 2, length),
                )

    def test_resets_after_filling_dictionary(self):
        randomizer = random.Random(20260816)
        indices = bytes(
            randomizer.randrange(256)
            for _ in range(100000)
        )

        payload = _encode_lzw_indices(indices, 8)
        codes = _unpack_codes(payload, 8)

        self.assertGreater(codes.count(256), 1)
        self.assertEqual(257, codes[-1])
        self.assertEqual(
            indices,
            _decode_lzw_indices(payload, 8, len(indices)),
        )

    def test_rejects_invalid_indices_and_output_limit(self):
        with self.assertRaisesRegex(_GifLzwError, "literal range"):
            _encode_lzw_indices(bytes((4,)), 2)

        limits = _GifLzwLimits(max_candidate_bytes=1)
        with self.assertRaisesRegex(_GifLzwError, "candidate limit"):
            _encode_lzw_indices(b"\x00\x01", 2, limits=limits)


if __name__ == "__main__":
    unittest.main()
