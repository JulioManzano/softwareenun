import graphene

from graphene_django_extras import DjangoListObjectField

from core.models import PublicFile

from .types import (
    PublicFileListType,
    PublicFileProjectListType,
)

from .filters import (
    PublicFileFilter,
    PublicFileProjectFilter,
)


class Query(graphene.ObjectType):

    public_files = DjangoListObjectField(
        PublicFileListType,
        filterset_class=PublicFileFilter,
    )

    def resolve_public_files(self, info, **kwargs):
        print("🔥🔥🔥 ENTRÓ A resolve_public_files")
        print("ARGS:", kwargs)

        queryset = PublicFile.objects.all()

        print("TOTAL:", queryset.count())

        return queryset

    public_file_projects = DjangoListObjectField(
        PublicFileProjectListType,
        filterset_class=PublicFileProjectFilter,
    )