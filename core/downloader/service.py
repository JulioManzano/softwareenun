class DownloaderService:

    def __init__(self, providers):
        self.providers = providers

    def get_info(self, url):
        errors = []

        for provider in self.providers:
            try:
                data = provider.get_info(url)
    
                print(
                    f"DOWNLOAD PROVIDER SUCCESS: "
                    f"{provider.__class__.__name__}"
                )

                return data

            except Exception as e:
                print(
                    f"DOWNLOAD PROVIDER ERROR: "
                    f"{provider.__class__.__name__}: {e}"
                )

                errors.append(
                    f"{provider.__class__.__name__}: {e}"
                )

        raise Exception(
            "No downloader provider available: "
            + " | ".join(errors)
        )