from django.test import SimpleTestCase

from streaming.extractors.elnueve import ElnueveStreamExtractor


class ElnueveYoutubeExtractorTests(SimpleTestCase):
    def test_extracts_id_from_embed_url(self):
        self.assertEqual(
            ElnueveStreamExtractor._youtube_video_id(
                "https://www.youtube.com/embed/e4VpCP8KWLY?autoplay=1"
            ),
            "e4VpCP8KWLY",
        )

    def test_extracts_id_from_watch_url(self):
        self.assertEqual(
            ElnueveStreamExtractor._youtube_video_id(
                "https://www.youtube.com/watch?v=e4VpCP8KWLY"
            ),
            "e4VpCP8KWLY",
        )

    def test_rejects_non_video_youtube_url(self):
        self.assertIsNone(
            ElnueveStreamExtractor._youtube_video_id(
                "https://www.youtube.com/embed/live_stream?channel=UC123"
            )
        )