import django_filters

from .models import PublicFile, PublicFileProject


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


class PublicFileProjectFilter(django_filters.FilterSet):

    slug = django_filters.CharFilter(
        field_name="slug"
    )

    class Meta:
        model = PublicFileProject
        fields = (
            "slug",
        )