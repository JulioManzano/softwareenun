
from django.contrib import admin
from .models import PublicFile
import config.logger_setup 
from django.utils.html import format_html

@admin.register(PublicFile)
class PublicFileAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "id",
        "name",
        "file",
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
        "preview",
    )

    fields = (
        "file",
        "preview",
        "name",
        "is_public",
        "created_at",
    )

    @admin.display(description="Vista previa")
    def thumbnail(self, obj):
        if not obj.file:
            return "-"

        return format_html(
            '<img src="{}" style="width:80px;height:80px;'
            'object-fit:cover;border-radius:6px;" />',
            obj.file.url,
        )

    @admin.display(description="Vista previa")
    def preview(self, obj):
        if not obj.file:
            return "-"

        return format_html(
            '<img src="{}" style="max-width:500px;max-height:400px;'
            'object-fit:contain;border-radius:8px;" />',
            obj.file.url,
        )