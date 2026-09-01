import requests

from .base import DownloaderProvider


class YoinkuProvider(DownloaderProvider):

    BASE_URL = "https://yoinku.com/api/v1"

    def __init__(self, api_key):
        self.api_key = api_key

    @property
    def headers(self):
        return {
            "x-api-key": self.api_key,
        }

    def get_info(self, url):
        response = requests.get(
            f"{self.BASE_URL}/info",
            params={"url": url},
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            raise Exception(
                data.get("error", {}).get(
                    "message",
                    "Yoinku error",
                )
            )

        return self._normalize_info(data["data"])

    def _normalize_info(self, data):
        formats = []

        for fmt in data.get("formats", []):
            formats.append({
                "format_id": fmt.get("id"),
                "kind": fmt.get("kind"),
                "container": fmt.get("container"),
                "quality": fmt.get("quality"),
                "width": fmt.get("width"),
                "height": fmt.get("height"),
                "fps": fmt.get("fps"),
                "audio_bitrate_kbps": fmt.get(
                    "audioBitrateKbps"
                ),
                "has_video": fmt.get("hasVideo", False),
                "has_audio": fmt.get("hasAudio", False),
                "filesize_bytes": fmt.get(
                    "filesizeBytes"
                ),
                "estimated": fmt.get(
                    "estimated",
                    False,
                ),
            })

        return {
            "title": data.get("title"),
            "author": data.get("author"),
            "thumbnail": data.get("thumbnailUrl"),
            "duration_seconds": data.get(
                "durationSeconds"
            ),
            "formats": formats,
        }

    def get_download_url(self, url, format_id):
        response = requests.get(
            f"{self.BASE_URL}/download",
            params={
                "url": url,
                "format": format_id,
            },
            headers=self.headers,
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            raise Exception(
                data.get("error", {}).get(
                    "message",
                    "Yoinku error",
                )
            )

        return data