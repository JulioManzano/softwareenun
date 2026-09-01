import graphene

from .factory import get_downloader_service
from .types import DownloadInfoType, DownloadResultType


class GetDownloadInfo(graphene.Mutation):

    class Arguments:
        url = graphene.String(required=True)

    Output = DownloadInfoType

    @staticmethod
    def mutate(root, info, url):
        try:
            service = get_downloader_service()

            data = service.get_info(url)

            print("\n=== DOWNLOAD INFO MUTATION ===")
            print("DATA:", data)

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
            print("\n=== DOWNLOAD INFO ERROR ===")
            print("ERROR:", repr(e))

            return DownloadInfoType(
                success=False,
                message=str(e),
                formats=[],
            )
            
class GetDownloadUrl(graphene.Mutation):

    class Arguments:
        url = graphene.String(required=True)
        format_id = graphene.String(required=True)

    Output = DownloadResultType

    @staticmethod
    def mutate(root, info, url, format_id):
        try:
            service = get_downloader_service()

            result = service.get_download_url(
                url=url,
                format_id=format_id,
            )

            print("\n=== DOWNLOAD URL RESULT ===")
            print(result)

            return DownloadResultType(
                success=True,
                message="Descarga preparada correctamente",
                url=result.get("url"),
                filename=result.get("filename"),
                format_id=result.get("format_id"),
                expires_in_seconds=result.get(
                    "expires_in_seconds"
                ),
            )

        except Exception as e:
            print(
                "\n=== DOWNLOAD URL ERROR ==="
            )
            print("ERROR:", repr(e))

            return DownloadResultType(
                success=False,
                message=str(e),
            )