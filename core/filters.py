import django_filters

from .models import PublicFile, PublicFileProject


class PublicFileFilter(django_filters.FilterSet):

    project_id = django_filters.NumberFilter(
        field_name="project_id"
    )

    project_slug = django_filters.CharFilter(
        field_name="project__slug",
        lookup_expr="iexact",
    )

    slug = django_filters.CharFilter(
        lookup_expr="iexact",
    )

    ordering = django_filters.CharFilter(
        method="filter_ordering"
    )

    class Meta:
        model = PublicFile
        fields = [
            "id",
            "project_id",
            "project_slug",
            "slug",
            "ordering",
        ]

    def filter_ordering(self, queryset, name, value):
        allowed_fields = [
            "name", "-name",
            "created_at", "-created_at",
            "slug", "-slug",
        ]

        if value in allowed_fields:
            return queryset.order_by(value)

        return queryset.order_by("-created_at")


class PublicFileProjectFilter(django_filters.FilterSet):

    slug = django_filters.CharFilter(
        lookup_expr="iexact",
    )

    ordering = django_filters.CharFilter(
        method="filter_ordering"
    )

    class Meta:
        model = PublicFileProject
        fields = [
            "id",
            "name",
            "slug",
            "ordering",
        ]

    def filter_ordering(self, queryset, name, value):
        allowed_fields = [
            "name", "-name",
            "created_at", "-created_at",
            "slug", "-slug",
        ]

        if value in allowed_fields:
            return queryset.order_by(value)

        return queryset.order_by("name")