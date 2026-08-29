from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoListObjectType
from graphene_django_extras.paginations import LimitOffsetGraphqlPagination

from .models import PublicFile, PublicFileProject


class PublicFileListType(DjangoListObjectType):
    class Meta:
        model = PublicFile
        pagination = LimitOffsetGraphqlPagination(default_limit=25)


class PublicFileType(DjangoObjectType):
    class Meta:
        model = PublicFile
        fields = "__all__"


class PublicFileProjectListType(DjangoListObjectType):
    class Meta:
        model = PublicFileProject
        pagination = LimitOffsetGraphqlPagination(default_limit=25)


class PublicFileProjectType(DjangoObjectType):
    class Meta:
        model = PublicFileProject
        fields = "__all__"