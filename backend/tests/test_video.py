import subprocess
import tempfile
import unittest
from pathlib import Path

from jukebox import video


def make_movie(path: Path, codec_args: list[str], size: str = "320x180") -> None:
    subprocess.run([video.ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"testsrc=size={size}:rate=10:duration=1", *codec_args, str(path)],
                   check=True)


class TestVideo(unittest.TestCase):
    def test_h264_filename(self):
        self.assertEqual(video.h264_filename("a_2160p30_h265.mp4"), "a_2160p30_h264.mp4")
        self.assertEqual(video.h264_filename("clip.mov"), "clip_h264.mp4")
        self.assertEqual(video.h264_filename("b_h264.mp4"), "b_h264.mp4")

    def test_reencodes_to_browser_h264(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.mp4"
            # MPEG-4 Part 2 stands in for a non-browser movie (the bundled ffmpeg may lack an H.265 encoder)
            make_movie(src, ["-c:v", "mpeg4", "-pix_fmt", "yuv420p"])
            out = Path(tmp) / "out.mp4"
            out.write_bytes(video.to_h264(src.read_bytes()))
            self.assertEqual(video.probe(out)[:2], ("h264", "yuv420p"))

    def test_scales_wide_movies(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "wide.mp4"
            make_movie(src, ["-c:v", "mpeg4"], size="5120x1440")
            out = Path(tmp) / "out.mp4"
            out.write_bytes(video.to_h264(src.read_bytes()))
            self.assertEqual(video.probe(out)[2], video.MAX_WIDTH)

    def test_keeps_compatible_h264(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "ok.mp4"
            make_movie(src, ["-c:v", "libx264", "-pix_fmt", "yuv420p"])
            data = src.read_bytes()
            self.assertIs(video.to_h264(data), data)

    def test_bad_input_raises(self):
        with self.assertRaises(RuntimeError):
            video.to_h264(b"not a movie")


if __name__ == "__main__":
    unittest.main()
