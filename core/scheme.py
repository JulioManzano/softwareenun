import graphene

from graphene_django_extras import DjangoListObjectField

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

    public_file_projects = DjangoListObjectField(
        PublicFileProjectListType,
        filterset_class=PublicFileProjectFilter,
    )