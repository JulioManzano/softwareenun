import django_filters
import graphene

from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .models import PublicFile, PublicFileProject


class PublicFileProjectType(DjangoObjectType):
    class Meta:
        model = PublicFileProject
        fields = (
            "id",
            "name",
            "slug",
        )


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


class PublicFileFilter(django_filters.FilterSet):
    project_id = django_filters.NumberFilter(
        field_name="project_id"
    )

    project_slug = django_filters.CharFilter(
        field_name="project__slug"
    )

    slug = django_filters.CharFilter(
        field_name="slug"
    )

    class Meta:
        model = PublicFile
        fields = (
            "project_id",
            "project_slug",
            "slug",
        )


class Query(graphene.ObjectType):

    public_file_projects = graphene.List(
        PublicFileProjectType
    )

    public_files = DjangoFilterConnectionField(
        PublicFileType,
        filterset_class=PublicFileFilter,
    )

    def resolve_public_file_projects(self, info):
        return PublicFileProject.objects.all()

    def resolve_public_files(self, info, **kwargs):
        return PublicFile.objects.filter(
            is_public=True
        )
