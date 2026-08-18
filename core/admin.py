
from django.contrib import admin
from .models import PublicFile


@admin.register(PublicFile)
class PublicFileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "is_public",
        "created_at",
    )

    list_filter = (
        "is_public",
        "created_at",
    )

    search_fields = (
        "name",
        "file",
    )

    readonly_fields = (
        "created_at",
    )