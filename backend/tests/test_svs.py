import unittest
from unittest.mock import Mock, patch

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


if __name__ == "__main__":
    unittest.main()
