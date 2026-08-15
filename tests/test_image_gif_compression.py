"""Regression tests for the public animated-GIF compression path."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from poimage import compress_image


def _snapshot(path):
    with Image.open(path) as image:
        frames = []
        durations = []
        for index in range(image.n_frames):
            image.seek(index)
            durations.append(image.info.get("duration"))
            frames.append(image.convert("RGBA").tobytes())
        return (
            image.size,
            image.n_frames,
            image.info.get("loop"),
            tuple(durations),
            tuple(frames),
        )


def _create_two_frame_gif(path):
    first = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    ImageDraw.Draw(first).rectangle((0, 0, 3, 7), fill=(255, 0, 0, 255))
    second = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    ImageDraw.Draw(second).rectangle((4, 0, 7, 7), fill=(0, 0, 255, 255))
    first.save(
        path,
        format="GIF",
        save_all=True,
        append_images=[second],
        duration=[70, 130],
        loop=3,
        disposal=[2, 1],
        optimize=False,
    )


def _create_transparent_moving_gif(path):
    frames = []
    for index in range(12):
        frame = Image.new("RGBA", (48, 32), (0, 0, 0, 0))
        ImageDraw.Draw(frame).rectangle(
            (index * 3, 8, index * 3 + 8, 23),
            fill=(255, 40, 20, 255),
        )
        frames.append(frame)
    frames[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[40 + (index % 3) * 10 for index in range(12)],
        loop=0,
        disposal=2,
        optimize=False,
    )


class TestAnimatedGifCompression(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_preserves_animation_and_uses_smaller_verified_candidate(self):
        source = self.root / "source.gif"
        output = self.root / "output.gif"
        _create_transparent_moving_gif(source)

        before = _snapshot(source)
        compress_image(str(source), str(output), quality=10)

        self.assertEqual(before, _snapshot(output))
        self.assertLess(output.stat().st_size, source.stat().st_size)

    def test_quality_is_ignored_for_animated_gif(self):
        source = self.root / "source.gif"
        low = self.root / "low.gif"
        high = self.root / "high.gif"
        _create_transparent_moving_gif(source)

        compress_image(str(source), str(low), quality=5)
        compress_image(str(source), str(high), quality=95)

        self.assertEqual(low.read_bytes(), high.read_bytes())
        self.assertEqual(_snapshot(source), _snapshot(low))

    def test_copies_original_bytes_when_no_smaller_candidate_exists(self):
        source = self.root / "source.gif"
        output = self.root / "output.gif"
        _create_two_frame_gif(source)

        compress_image(str(source), str(output), quality=60)

        self.assertEqual(source.read_bytes(), output.read_bytes())
        self.assertEqual(_snapshot(source), _snapshot(output))

    def test_same_input_and_output_path_is_safe(self):
        source = self.root / "source.gif"
        _create_two_frame_gif(source)
        digest = hashlib.sha256(source.read_bytes()).digest()

        compress_image(str(source), str(source), quality=60)

        self.assertEqual(digest, hashlib.sha256(source.read_bytes()).digest())
        self.assertEqual(2, _snapshot(source)[1])

    def test_non_gif_raster_path_still_works(self):
        source = self.root / "source.jpg"
        output = self.root / "output.jpg"
        Image.new("RGB", (32, 32), (80, 120, 160)).save(source, format="JPEG", quality=95)

        compress_image(str(source), str(output), quality=70)

        with Image.open(output) as image:
            self.assertEqual("JPEG", image.format)
            self.assertEqual((32, 32), image.size)


if __name__ == "__main__":
    unittest.main()
