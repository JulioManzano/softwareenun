import graphene
from graphene_django_extras import DjangoListObjectField
from core.models import PublicFile
from graphene_file_upload.scalars import Upload
from core.services.replicate_service import ReplicateService

from .types import (
    PublicFileListType,
    PublicFileProjectListType,
    PublicFileType,
)

from .filters import (
    PublicFileFilter,
    PublicFileProjectFilter,
)



class Query(graphene.ObjectType):

    public_files = graphene.List(
        PublicFileType,
        project_id=graphene.Decimal(),
    )

    def resolve_public_files(self, info, project_id=None):

        queryset = PublicFile.objects.all()

        if project_id:
            queryset = queryset.filter(
                project_id=project_id
            )

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


class Mutation(graphene.ObjectType):

    enhance_image = EnhanceImageMutation.Field()
