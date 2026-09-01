from django.conf import settings

from .providers.yoinku import YoinkuProvider
from .providers.tunelio import TunelioProvider
from .service import DownloaderService


def get_downloader_service():
    return DownloaderService([
        YoinkuProvider(
            settings.YOINKU_API_KEY
        ),
        TunelioProvider(
            settings.TUNELIO_API_KEY
        ),
    ])