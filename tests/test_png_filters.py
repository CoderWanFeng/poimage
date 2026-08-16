"""Round-trip tests for PNG scanline filters."""

import unittest

from poimage.lib.image.png_filters import (
    _filter_plans,
    _forward_filter,
    _inverse_filter,
    _paeth,
)


class TestPngFilters(unittest.TestCase):
    def test_all_filter_types_round_trip(self):
        raw = bytes((10, 20, 30, 40, 50, 60, 70, 80))
        previous = bytes((1, 2, 3, 4, 5, 6, 7, 8))
        for bpp in (1, 2, 4):
            for filter_type in range(5):
                with self.subTest(bpp=bpp, filter_type=filter_type):
                    filtered = _forward_filter(raw, previous, bpp, filter_type)
                    self.assertEqual(
                        raw,
                        _inverse_filter(filtered, previous, bpp, filter_type),
                    )

    def test_filter_plans_are_deterministic_unique_and_bounded(self):
        rows = [bytes(range(16)), bytes(reversed(range(16)))]
        first = _filter_plans(rows, 1, (0, 0))
        second = _filter_plans(rows, 1, (0, 0))
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)))
        self.assertLessEqual(len(first), 6)
        self.assertTrue(all(len(plan) == len(rows) for plan in first))

    def test_paeth_tie_order(self):
        self.assertEqual(10, _paeth(10, 20, 30))


if __name__ == "__main__":
    unittest.main()
