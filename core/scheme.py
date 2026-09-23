import graphene
from graphene_django_extras import DjangoListObjectField
from .downloader.mutation import GetDownloadInfo,GetDownloadUrl
from core.models import PublicFile, PublicFileFolder, PublicFileProject
from graphene_file_upload.scalars import Upload
from core.services.replicate_service import ReplicateService

from .types import (
    PublicFileFolderType,
    PublicFileListType,
    PublicFileProjectListType,
    PublicFileType,
)

from .filters import (
    PublicFileFilter,
    PublicFileProjectFilter,
)



class Query(graphene.ObjectType):

    public_file_folders = graphene.List(
        PublicFileFolderType,
        project_id=graphene.ID(required=True),
        parent_id=graphene.ID(),
    )

    def resolve_public_file_folders(self, info, project_id, parent_id=None):
        queryset = PublicFileFolder.objects.filter(project_id=project_id)
        if parent_id:
            return queryset.filter(parent_id=parent_id)
        return queryset.filter(parent__isnull=True)

    public_files = graphene.List(
        PublicFileType,
        project_id=graphene.Decimal(),
        folder_id=graphene.ID(),
    )

    def resolve_public_files(self, info, project_id=None, folder_id=None):

        queryset = PublicFile.objects.filter(is_public=True)

        if project_id:
            queryset = queryset.filter(
                project_id=project_id
            )
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)

        return queryset

    public_file_projects = DjangoListObjectField(
        PublicFileProjectListType,
        filterset_class=PublicFileProjectFilter,
    )
    
class EnhanceImageMutation(graphene.Mutation):

    class Arguments:
        image = Upload(required=True)
        scale = graphene.Int(default_value=2)
        face_enhance = graphene.Boolean(default_value=False)

    success = graphene.Boolean()
    url = graphene.String()
    error = graphene.String()

    @classmethod
    def mutate(
        cls,
        root,
        info,
        image,
        scale=2,
        face_enhance=False,
    ):
        try:

            print("=== ENHANCE IMAGE MUTATION ===")
            print("Image:", getattr(image, "name", None))
            print("Size:", getattr(image, "size", None))
            print("Scale:", scale)
            print("Face enhance:", face_enhance)

            if scale not in [2, 4]:
                return cls(
                    success=False,
                    error="La escala debe ser 2 o 4.",
                )

            url = ReplicateService.enhance_image(
                image_file=image,
                scale=scale,
                face_enhance=face_enhance,
            )

            print("Enhanced URL:", url)

            return cls(
                success=True,
                url=url,
            )

        except Exception as e:

            print(
                "ERROR ENHANCE IMAGE MUTATION:",
                e,
            )

            return cls(
                success=False,
                error=str(e),
            )

class UploadPublicFileMutation(graphene.Mutation):

    class Arguments:
        project_id = graphene.ID(required=True)
        file = Upload(required=True)
        name = graphene.String()
        folder_id = graphene.ID()

    success = graphene.Boolean()
    file = graphene.Field(PublicFileType)
    error = graphene.String()

    @classmethod
    def mutate(
        cls,
        root,
        info,
        project_id,
        file,
        name=None,
    ):
        try:
            print("=== UPLOAD PUBLIC FILE ===")
            print("Project ID:", project_id)
            print("File:", getattr(file, "name", None))
            print("Size:", getattr(file, "size", None))
            print("Name:", name)

            try:
                project = PublicFileProject.objects.get(
                    id=project_id
                )
            except PublicFileProject.DoesNotExist:
                return cls(
                    success=False,
                    error="El proyecto no existe.",
                )

            file_name = name or file.name
            folder = None
            if folder_id:
                try:
                    folder = PublicFileFolder.objects.get(
                        id=folder_id,
                        project=project,
                    )
                except PublicFileFolder.DoesNotExist:
                    return cls(
                        success=False,
                        error="La carpeta no existe o no pertenece al proyecto.",
                    )

            public_file = PublicFile.objects.create(
                project=project,
                folder=folder,
                file=file,
                name=file_name,
                is_public=True,
            )

            print(
                "Public file created:",
                public_file.id,
                public_file.file.url,
            )

            return cls(
                success=True,
                file=public_file,
            )

        except Exception as e:
            print(
                "ERROR UPLOAD PUBLIC FILE:",
                e,
            )

            return cls(
                success=False,
                error=str(e),
            )
            
class Mutation(graphene.ObjectType):
    upload_public_file = UploadPublicFileMutation.Field()
    enhance_image = EnhanceImageMutation.Field()

    get_download_info = GetDownloadInfo.Field()
    get_download_url = GetDownloadUrl.Field()
