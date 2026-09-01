from abc import ABC, abstractmethod


class DownloaderProvider(ABC):

    @abstractmethod
    def get_info(self, url):
        pass

    @abstractmethod
    def get_download_url(self, url, format_id):
        pass