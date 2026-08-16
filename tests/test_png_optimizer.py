"""Focused tests for the native PNG optimizer."""

import io
import random
import unittest

from PIL import Image

from poimage.lib.image.png_chunks import _parse_png
from poimage.lib.image.png_filters import _inflate_rows
from poimage.lib.image.png_optimizer import _optimize_png_idat_losslessly


def _png_bytes(image, **kwargs):
    output = io.BytesIO()
    image.save(output, format="PNG", **kwargs)
    return output.getvalue()


class TestPngOptimizer(unittest.TestCase):
    def test_candidate_is_smaller_lossless_and_idempotent(self):
        source = _png_bytes(Image.new("RGBA", (64, 64), (10, 20, 30, 40)))
        candidate = _optimize_png_idat_losslessly(source)

        self.assertIsNotNone(candidate)
        self.assertLess(len(candidate), len(source))
        self.assertEqual(
            _inflate_rows(_parse_png(source))[0],
            _inflate_rows(_parse_png(candidate))[0],
        )
        self.assertIsNone(_optimize_png_idat_losslessly(candidate))

    def test_only_contiguous_idat_run_changes(self):
        source = _png_bytes(Image.new("RGB", (32, 32), "orange"))
        source_document = _parse_png(source)
        candidate = _optimize_png_idat_losslessly(source)
        candidate_document = _parse_png(candidate)

        self.assertEqual(
            source[:source_document.idat_start],
            candidate[:candidate_document.idat_start],
        )
        self.assertEqual(
            source[source_document.idat_end:],
            candidate[candidate_document.idat_end:],
        )

    def test_random_noise_never_produces_a_larger_candidate(self):
        randomizer = random.Random(20260816)
        image = Image.new("RGB", (64, 64))
        image.putdata([
            (
                randomizer.randrange(256),
                randomizer.randrange(256),
                randomizer.randrange(256),
            )
            for _ in range(64 * 64)
        ])
        source = _png_bytes(image, optimize=True, compress_level=9)

        candidate = _optimize_png_idat_losslessly(source)

        self.assertTrue(candidate is None or len(candidate) < len(source))

    def test_corrupt_or_unsupported_input_declines(self):
        self.assertIsNone(_optimize_png_idat_losslessly(b"not a png"))


if __name__ == "__main__":
    unittest.main()
