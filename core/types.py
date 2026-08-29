import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoListObjectType

from .models import PublicFile, PublicFileProject


class PublicFileType(DjangoObjectType):
    class Meta:
        model = PublicFile
        fields = (
            "id",
            "project",
            "file",
            "name",
            "slug",
            "created_at",
            "is_public",
        )


class PublicFileListType(DjangoListObjectType):
    class Meta:
        model = PublicFile
        fields = (
            "id",
            "project",
            "file",
            "name",
            "slug",
            "created_at",
            "is_public",
        )


class PublicFileProjectType(DjangoObjectType):
    class Meta:
        model = PublicFileProject
        fields = (
            "id",
            "name",
            "slug",
            "created_at",
        )


class PublicFileProjectListType(DjangoListObjectType):
    class Meta:
        model = PublicFileProject
        fields = (
            "id",
            "name",
            "slug",
            "created_at",
        )