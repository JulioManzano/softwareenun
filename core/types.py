
import graphene

from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoListObjectType
from graphene_django_extras.paginations import LimitOffsetGraphqlPagination

from .models import PublicFile, PublicFileFolder, PublicFileProject


class PublicFileType(DjangoObjectType):

    file = graphene.String()
    folder = graphene.Field(lambda: PublicFileFolderType)

    class Meta:
        model = PublicFile
        fields = "__all__"

    def resolve_file(self, info):
        print("🔥 RESOLVE FILE EJECUTADO")
        print("FILE:", self.file)
        print("NAME:", self.file.name)
        print("URL:", self.file.url)

        if not self.file:
            return None

        return info.context.build_absolute_uri(
            self.file.url
        )


class PublicFileListType(DjangoListObjectType):

    class Meta:
        model = PublicFile
        pagination = LimitOffsetGraphqlPagination(default_limit=25)

class PublicFileProjectType(DjangoObjectType):

    files = graphene.List(PublicFileType)
    folders = graphene.List(lambda: PublicFileFolderType)

    class Meta:
        model = PublicFileProject
        fields = "__all__"

    def resolve_files(self, info):
        return self.files.filter(
            is_public=True
        )

    def resolve_folders(self, info):
        return self.folders.filter(parent__isnull=True)


class PublicFileFolderType(DjangoObjectType):

    children = graphene.List(lambda: PublicFileFolderType)
    files = graphene.List(lambda: PublicFileType)

    class Meta:
        model = PublicFileFolder
        fields = "__all__"

    def resolve_children(self, info):
        return self.children.all()

    def resolve_files(self, info):
        return self.files.filter(is_public=True)


class PublicFileProjectListType(DjangoListObjectType):

    class Meta:
        model = PublicFileProject
        pagination = LimitOffsetGraphqlPagination(default_limit=25)
