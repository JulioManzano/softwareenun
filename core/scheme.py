import graphene

from graphene_django_extras import DjangoListObjectField

from core.models import PublicFile

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