import json
import subprocess

import graphene


class DownloadFormatType(graphene.ObjectType):
    format_id = graphene.String()
    label = graphene.String()
    ext = graphene.String()
    height = graphene.Int()
    filesize = graphene.Int()
    has_audio = graphene.Boolean()
    has_video = graphene.Boolean()


class DownloadInfoType(graphene.ObjectType):
    success = graphene.Boolean()
    message = graphene.String()
    title = graphene.String()
    thumbnail = graphene.String()
    duration = graphene.Int()
    formats = graphene.List(DownloadFormatType)


class GetDownloadInfo(graphene.Mutation):
    class Arguments:
        url = graphene.String(required=True)

    Output = DownloadInfoType

    @staticmethod
    def mutate(root, info, url):
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-J",
                    "--no-playlist",
                    url,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            data = json.loads(result.stdout)

            formats = []

            for fmt in data.get("formats", []):
                has_video = (
                    fmt.get("vcodec")
                    and fmt.get("vcodec") != "none"
                )

                has_audio = (
                    fmt.get("acodec")
                    and fmt.get("acodec") != "none"
                )

                height = fmt.get("height")

                # Ignoramos formatos que no tengan video ni audio
                if not has_video and not has_audio:
                    continue

                # Formatos de video
                if has_video:
                    if height:
                        label = f"{height}p"
                    else:
                        label = "Video"

                    if has_audio:
                        label += " + Audio"

                # Formatos solamente de audio
                else:
                    label = "Audio"

                formats.append(
                    DownloadFormatType(
                        format_id=fmt.get("format_id"),
                        label=label,
                        ext=fmt.get("ext"),
                        height=height,
                        filesize=fmt.get("filesize"),
                        has_audio=has_audio,
                        has_video=has_video,
                    )
                )

            # Ordenamos video de mayor a menor resolución
            formats.sort(
                key=lambda x: (
                    x.height or 0,
                    x.has_video,
                ),
                reverse=True,
            )

            return DownloadInfoType(
                success=True,
                message="Información obtenida correctamente",
                title=data.get("title"),
                thumbnail=data.get("thumbnail"),
                duration=data.get("duration"),
                formats=formats,
            )

        except subprocess.CalledProcessError as e:
            return DownloadInfoType(
                success=False,
                message=e.stderr or "No se pudo obtener la información",
                formats=[],
            )

        except Exception as e:
            return DownloadInfoType(
                success=False,
                message=str(e),
                formats=[],
            )