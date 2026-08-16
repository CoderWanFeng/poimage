"""Tests for strict bounded PNG chunk parsing."""

import io
import struct
import unittest
import zlib

from PIL import Image

from poimage.lib.image.png_chunks import (
    _PngFormatError,
    _PngLimits,
    _parse_png,
)


def _png_bytes(mode="RGBA"):
    output = io.BytesIO()
    color = (1, 2, 3, 4) if mode == "RGBA" else (1, 2, 3)
    Image.new(mode, (8, 6), color).save(output, format="PNG")
    return output.getvalue()


def _chunk(chunk_type, payload):
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


class TestPngChunks(unittest.TestCase):
    def test_parses_valid_static_png(self):
        document = _parse_png(_png_bytes())
        self.assertEqual((8, 6, 8, 6), (
            document.width, document.height, document.bit_depth, document.color_type
        ))
        self.assertGreater(len(document.idat_payload), 0)

    def test_rejects_signature_crc_and_trailing_data(self):
        valid = _png_bytes()
        cases = (
            b"not png" + valid[7:],
            valid[:20] + bytes((valid[20] ^ 1,)) + valid[21:],
            valid + b"trailing",
        )
        for data in cases:
            with self.subTest(length=len(data)):
                with self.assertRaises(_PngFormatError):
                    _parse_png(data)

    def test_rejects_excessive_row_count(self):
        with self.assertRaisesRegex(_PngFormatError, "row limit"):
            _parse_png(_png_bytes(), limits=_PngLimits(max_rows=5))

    def test_rejects_apng_control_chunk(self):
        valid = _png_bytes()
        document = _parse_png(valid)
        chunk = _chunk(b"acTL", struct.pack(">II", 2, 0))
        data = valid[:document.idat_start] + chunk + valid[document.idat_start:]
        with self.assertRaisesRegex(_PngFormatError, "APNG"):
            _parse_png(data)

    def test_unknown_ancillary_safe_to_copy_bit_is_honored(self):
        valid = _png_bytes()
        document = _parse_png(valid)
        safe = _chunk(b"raNd", b"safe")
        unsafe = _chunk(b"raND", b"unsafe")

        _parse_png(
            valid[:document.idat_start] + safe + valid[document.idat_start:]
        )
        with self.assertRaisesRegex(_PngFormatError, "unsafe-to-copy"):
            _parse_png(
                valid[:document.idat_start]
                + unsafe
                + valid[document.idat_start:]
            )

    def test_truecolor_plte_is_limited_to_256_entries(self):
        valid = _png_bytes(mode="RGB")
        document = _parse_png(valid)
        oversized_plte = _chunk(b"PLTE", bytes(257 * 3))
        data = (
            valid[:document.idat_start]
            + oversized_plte
            + valid[document.idat_start:]
        )
        with self.assertRaisesRegex(_PngFormatError, "palette"):
            _parse_png(data)


if __name__ == "__main__":
    unittest.main()
