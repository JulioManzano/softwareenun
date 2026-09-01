import graphene

from .factory import get_downloader_service
from .types import DownloadInfoType


class GetDownloadInfo(graphene.Mutation):

    class Arguments:
        url = graphene.String(required=True)

    Output = DownloadInfoType

    @staticmethod
    def mutate(root, info, url):
        try:
            service = get_downloader_service()

            result = service.get_info(url)

            data = result["data"]

            return DownloadInfoType(
                success=True,
                message="Información obtenida correctamente",
                title=data.get("title"),
                author=data.get("author"),
                thumbnail=data.get("thumbnail"),
                duration_seconds=data.get(
                    "duration_seconds"
                ),
                formats=data.get("formats", []),
            )

        except Exception as e:
            return DownloadInfoType(
                success=False,
                message=str(e),
                formats=[],
            )