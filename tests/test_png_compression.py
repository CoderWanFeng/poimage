"""Public regression tests for lossless PNG compression."""

import os
from pathlib import Path
import random
import struct
import tempfile
import unittest
import zlib
from unittest import mock

from PIL import Image, PngImagePlugin

from poimage import compress_image
from poimage.lib.image.png_chunks import _DEFAULT_PNG_LIMITS, _parse_png


def _save_png(path, mode="RGBA", size=(64, 64), metadata=False):
    if mode == "1":
        image = Image.new(mode, size, 1)
    elif mode == "L":
        image = Image.new(mode, size, 127)
    elif mode == "LA":
        image = Image.new(mode, size, (127, 80))
    elif mode == "P":
        image = Image.new(mode, size, 1)
        image.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
        image.info["transparency"] = 0
    elif mode == "RGB":
        image = Image.new(mode, size, (10, 20, 30))
    else:
        image = Image.new(mode, size, (10, 20, 30, 80))

    kwargs = {}
    if metadata:
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("note", "keep this metadata")
        kwargs["pnginfo"] = pnginfo
        kwargs["dpi"] = (144, 144)
    image.save(path, format="PNG", **kwargs)


def _snapshot(path):
    with Image.open(path) as image:
        return (
            image.mode,
            image.size,
            image.tobytes(),
            image.info.get("transparency"),
            image.info.get("note"),
            image.info.get("dpi"),
        )


def _chunk(chunk_type, payload):
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


class TestPngCompression(unittest.TestCase):
    def test_static_png_preserves_pixels_and_never_grows(self):
        for mode in ("1", "L", "LA", "P", "RGB", "RGBA"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.png"
                output = root / "output.png"
                _save_png(source, mode=mode)
                expected = _snapshot(source)
                source_size = source.stat().st_size

                compress_image(str(source), str(output), 50)

                self.assertEqual(expected, _snapshot(output))
                self.assertLessEqual(output.stat().st_size, source_size)

    def test_metadata_and_non_idat_content_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "output.png"
            _save_png(source, metadata=True)
            expected = _snapshot(source)

            compress_image(str(source), str(output), 50)

            self.assertEqual(expected, _snapshot(output))
            self.assertLessEqual(output.stat().st_size, source.stat().st_size)

    def test_flat_png_gets_smaller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "output.png"
            Image.new("RGBA", (512, 512), (10, 20, 30, 40)).save(
                source,
                format="PNG",
                compress_level=6,
            )

            compress_image(str(source), str(output), 5)

            self.assertLess(output.stat().st_size, source.stat().st_size)
            self.assertEqual(_snapshot(source), _snapshot(output))

    def test_already_optimized_and_noisy_pngs_never_grow(self):
        randomizer = random.Random(20260816)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = []

            optimized = root / "optimized.png"
            _save_png(optimized, size=(32, 32))
            with Image.open(optimized) as image:
                image.save(optimized, optimize=True, compress_level=9)
            cases.append(optimized)

            noisy = root / "noise.png"
            image = Image.new("RGB", (64, 64))
            image.putdata([
                (
                    randomizer.randrange(256),
                    randomizer.randrange(256),
                    randomizer.randrange(256),
                )
                for _ in range(64 * 64)
            ])
            image.save(noisy, optimize=True, compress_level=9)
            cases.append(noisy)

            for source in cases:
                with self.subTest(source=source.name):
                    output = root / ("out-" + source.name)
                    before = source.read_bytes()
                    compress_image(str(source), str(output), 95)
                    self.assertLessEqual(len(output.read_bytes()), len(before))
                    self.assertEqual(_snapshot(source), _snapshot(output))

    def test_quality_does_not_change_png_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            low = root / "low.png"
            high = root / "high.png"
            _save_png(source)

            compress_image(str(source), str(low), 5)
            compress_image(str(source), str(high), 95)

            self.assertEqual(low.read_bytes(), high.read_bytes())

    def test_path_detection_in_place_and_bytes_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.dat"
            output = root / "output.PNG"
            _save_png(source)
            expected = _snapshot(source)

            compress_image(os.fsencode(source), os.fsencode(output), 50)
            self.assertEqual(expected, _snapshot(output))

            before = output.read_bytes()
            compress_image(str(output), str(output), 50)
            self.assertLessEqual(output.stat().st_size, len(before))
            self.assertEqual(expected, _snapshot(output))

    def test_non_png_and_file_like_inputs_keep_pillow_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jpeg = root / "source.jpg"
            png_from_jpeg = root / "converted.png"
            Image.new("RGB", (8, 8), "green").save(jpeg, format="JPEG")
            compress_image(str(jpeg), str(png_from_jpeg), 50)
            with Image.open(png_from_jpeg) as image:
                self.assertEqual("PNG", image.format)

            source = root / "source.png"
            stream_output = root / "stream-output.png"
            _save_png(source, mode="RGB")
            with source.open("rb") as stream:
                compress_image(stream, str(stream_output), 50)
            with Image.open(stream_output) as image:
                self.assertEqual("PNG", image.format)
                image.load()

    def test_apng_is_left_byte_for_byte_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "animated.png"
            output = root / "output.png"
            first = Image.new("RGBA", (8, 8), "red")
            second = Image.new("RGBA", (8, 8), "blue")
            first.save(
                source,
                format="PNG",
                save_all=True,
                append_images=[second],
                duration=[50, 70],
                loop=2,
            )
            expected = source.read_bytes()

            compress_image(str(source), str(output), 50)

            self.assertEqual(expected, output.read_bytes())


    def test_in_place_write_failure_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            Image.new("RGBA", (128, 128), (1, 2, 3, 4)).save(
                source, format="PNG", compress_level=0
            )
            expected = source.read_bytes()

            with mock.patch(
                "poimage.lib.image.png_compression.os.replace",
                side_effect=OSError("simulated replace failure"),
            ):
                with self.assertRaises(OSError):
                    compress_image(str(source), str(source), 50)

            self.assertEqual(expected, source.read_bytes())
            self.assertEqual([], list(root.glob(".source.png.*.tmp")))

    def test_large_png_uses_safe_fast_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "large.png"
            output = root / "output.png"
            Image.new("RGBA", (640, 480), (10, 20, 30, 40)).save(
                source, format="PNG", compress_level=1
            )
            expected = _snapshot(source)

            compress_image(str(source), str(output), 50)

            self.assertEqual(expected, _snapshot(output))
            self.assertLess(output.stat().st_size, source.stat().st_size)

    def test_unknown_unsafe_ancillary_chunk_disables_idat_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "output.png"
            Image.new("RGBA", (64, 64), (10, 20, 30, 40)).save(
                source, format="PNG", compress_level=0
            )
            original = source.read_bytes()
            document = _parse_png(original)
            marker = _chunk(b"raND", b"depends-on-critical-data")
            source.write_bytes(
                original[:document.idat_start]
                + marker
                + original[document.idat_start:]
            )
            expected = source.read_bytes()

            compress_image(str(source), str(output), 50)

            self.assertEqual(expected, output.read_bytes())

    def test_large_file_fallback_uses_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "output.png"
            _save_png(source)
            output.write_bytes(b"existing-output")
            expected = output.read_bytes()

            with mock.patch.object(
                _DEFAULT_PNG_LIMITS, "max_baseline_bytes", 1
            ), mock.patch(
                "poimage.lib.image.png_compression.os.replace",
                side_effect=OSError("simulated replace failure"),
            ):
                with self.assertRaises(OSError):
                    compress_image(str(source), str(output), 50)

            self.assertEqual(expected, output.read_bytes())
            self.assertEqual([], list(root.glob(".output.png.*.tmp")))

    def test_invalid_input_still_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.png"
            with self.assertRaises(FileNotFoundError):
                compress_image(str(missing), str(root / "out.png"), 50)


if __name__ == "__main__":
    unittest.main()
