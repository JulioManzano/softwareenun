import requests

from .base import DownloaderProvider


class TunelioProvider(DownloaderProvider):

    BASE_URL = "https://tunelio.dev"

    def __init__(self, api_key):
        self.api_key = api_key

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
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

        return self._normalize_info(data)

    def _normalize_info(self, data):
        formats = []

        for fmt in data.get("formats", []):
            quality = fmt.get("quality")

            formats.append({
                "format_id": f"video_{quality}",
                "kind": "video",
                "container": "mp4",
                "quality": quality,
                "width": fmt.get("width"),
                "height": fmt.get("height"),
                "fps": None,
                "audio_bitrate_kbps": None,
                "has_video": True,
                "has_audio": True,
                "filesize_bytes": fmt.get(
                    "file_size"
                ),
                "estimated": False,
            })

        audio = data.get("audioFormat")

        if audio:
            audio_format = audio.get("format")

            formats.append({
                "format_id": f"audio_{audio_format}",
                "kind": "audio",
                "container": audio_format,
                "quality": audio_format,
                "width": None,
                "height": None,
                "fps": None,
                "audio_bitrate_kbps": None,
                "has_video": False,
                "has_audio": True,
                "filesize_bytes": audio.get(
                    "file_size"
                ),
                "estimated": False,
            })

        return {
            "title": data.get("title"),
            "author": None,
            "thumbnail": data.get("thumbnail"),
            "duration_seconds": data.get(
                "duration_seconds"
            ),
            "formats": formats,
        }

    def get_download_url(self, url, format_id):
        if format_id.startswith("video_"):
            quality = format_id.replace(
                "video_",
                "",
                1,
            )
        elif format_id.startswith("audio_"):
            quality = format_id.replace(
                "audio_",
                "",
                1,
            )
        else:
            raise Exception(
                f"Invalid format: {format_id}"
            )

        response = requests.get(
            f"{self.BASE_URL}/create",
            params={
                "url": url,
                "quality": quality,
            },
            headers=self.headers,
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise Exception(
                data.get(
                    "error",
                    "Tunelio error",
                )
            )

        return data