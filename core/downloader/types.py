import graphene


class DownloadFormatType(graphene.ObjectType):
    format_id = graphene.String()
    kind = graphene.String()
    container = graphene.String()
    quality = graphene.String()
    width = graphene.Int()
    height = graphene.Int()
    fps = graphene.Int()
    audio_bitrate_kbps = graphene.Int()
    has_video = graphene.Boolean()
    has_audio = graphene.Boolean()
    filesize_bytes = graphene.Int()
    estimated = graphene.Boolean()


class DownloadInfoType(graphene.ObjectType):
    success = graphene.Boolean()
    message = graphene.String()
    title = graphene.String()
    author = graphene.String()
    thumbnail = graphene.String()
    duration_seconds = graphene.Int()
    formats = graphene.List(DownloadFormatType)