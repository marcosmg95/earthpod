import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import requests

from jukebox import svs

SAMPLE = {
    "id": 1,
    "media_groups": [
        {"title": "", "widget": "Video player", "items": [
            {"type": "media", "instance": {"url": "http://svs.gsfc.nasa.gov/vis/a.mp4", "filename": "a.mp4",
                                           "media_type": "Movie", "width": 1920, "height": 1080}},
            {"type": "media", "instance": {"url": "http://svs.gsfc.nasa.gov/vis/frames_pngs", "filename": "frames_pngs",
                                           "media_type": "Frames"}},
        ]},
        {"title": "Text", "widget": "Basic text with HTML", "items": [{"type": "text", "instance": None}]},
    ],
    "credits": [{"role": "Visualizer", "people": [{"name": "A", "employer": "NASA/GSFC"}, {"name": "B"}]}],
    "recommended_pages": [{"id": 7, "title": "Other", "page_type": "Visualization"}],
}


class TestSvs(unittest.TestCase):
    def test_media_items(self):
        items = svs.media_items(SAMPLE)
        self.assertEqual(len(items), 2)  # text item skipped
        self.assertEqual(items[0].url, "https://svs.gsfc.nasa.gov/vis/a.mp4")
        self.assertEqual((items[0].ext, items[0].media_type, items[0].group), ("mp4", "Movie", "Video player"))
        self.assertEqual(items[1].ext, "")  # frame folder, no extension

    def test_credits_and_links(self):
        self.assertEqual(svs.credits_text(SAMPLE), "Visualizer: A (NASA/GSFC), B")
        self.assertEqual(svs.linked_pages(SAMPLE)[0]["relation"], "recommended_pages")

    @patch("jukebox.svs.requests.get")
    def test_download_media(self, get):
        response = Mock()
        response.content = b"video"
        get.return_value = response

        self.assertEqual(svs.download_media("https://example.test/movie.mp4"), b"video")
        get.assert_called_once_with("https://example.test/movie.mp4", timeout=300)
        response.raise_for_status.assert_called_once_with()

    @patch("jukebox.svs.requests.get")
    def test_download_file_resumes_from_the_part_file(self, get):
        response = MagicMock(status_code=206)
        response.__enter__.return_value = response
        response.iter_content.return_value = [b"lo ", b"world"]
        get.return_value = response
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "movie.mp4"
            path.parent.mkdir()
            path.with_name("movie.mp4.part").write_bytes(b"hel")
            self.assertEqual(svs.download_file("https://example.test/movie.mp4", path), path)
            self.assertEqual(path.read_bytes(), b"hello world")
            self.assertFalse(path.with_name("movie.mp4.part").exists())
        self.assertEqual(get.call_args.kwargs["headers"], {"Range": "bytes=3-"})

    @patch("jukebox.svs.requests.get", side_effect=requests.ConnectionError)
    def test_download_file_gives_up(self, get):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                svs.download_file("https://example.test/x", Path(tmp) / "x", attempts=2, wait_s=0)
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
