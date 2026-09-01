class DownloaderService:

    def __init__(self, providers):
        self.providers = providers

    def get_info(self, url):
        errors = []

        for provider in self.providers:
            try:
                return provider.get_info(url)

            except Exception as e:
                errors.append(
                    f"{provider.__class__.__name__}: {str(e)}"
                )

        raise Exception(
            "No downloader provider available: "
            + " | ".join(errors)
        )

    def get_download_url(self, url, format_id):
        errors = []

        for provider in self.providers:
            try:
                return provider.get_download_url(
                    url,
                    format_id,
                )

            except Exception as e:
                errors.append(
                    f"{provider.__class__.__name__}: {str(e)}"
                )

        raise Exception(
            "No downloader provider available: "
            + " | ".join(errors)
        )