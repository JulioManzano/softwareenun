
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.shortcuts import render
from django.urls import path
from .models import PublicFile, PublicFileProject
import config.logger_setup 
from django.utils.html import format_html
import os
from django.conf import settings
from django import forms

from .services.public_file_sync import sync_public_files

class PublicFileAdminForm(forms.ModelForm):

    existing_file = forms.ChoiceField(
        label="Archivo existente",
        required=False,
        choices=[],
    )

    class Meta:
        model = PublicFile
        fields = "__all__"
        
    def save(self, commit=True):
        instance = super().save(commit=False)

        existing_file = self.cleaned_data.get("existing_file")

        if existing_file:
            instance.file.name = existing_file

        if commit:
            instance.save()

        return instance
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["file"].required = False

        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")

        # Archivos que ya están asignados a un PublicFile
        used_files = set(
            PublicFile.objects
            .exclude(file="")
            .values_list("file", flat=True)
        )

        choices = [("", "---------")]

        if os.path.exists(upload_dir):
            for root, dirs, files in os.walk(upload_dir):
                for filename in files:
                    full_path = os.path.join(root, filename)

                    relative_path = os.path.relpath(
                        full_path,
                        settings.MEDIA_ROOT,
                    ).replace(os.sep, "/")

                    # No mostrar archivos que ya están asignados
                    if relative_path in used_files:
                        continue

                    choices.append(
                        (
                            relative_path,
                            relative_path,
                        )
                    )

        self.fields["existing_file"].choices = choices
        
@admin.register(PublicFile)
class PublicFileAdmin(admin.ModelAdmin):
    form = PublicFileAdminForm

    class Media:
        js = ("admin/public_file_upload.js",)
        
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
        "project",
        "file",
        "existing_file",
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
        


class PublicFileInline(admin.TabularInline):
    model = PublicFile
    extra = 1

    fields = (
        "thumbnail",
        "file",
        "name",
        "is_public",
        "created_at",
    )

    readonly_fields = (
        "thumbnail",
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


@admin.register(PublicFileProject)
class PublicFileProjectAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/publicfileproject/change_list.html"

    list_display = (
        "name",
        "slug",
        "file_count",
        "created_at",
    )

    search_fields = (
        "name",
        "slug",
    )

    readonly_fields = (
        "created_at",
    )

    fields = (
        "name",
        "slug",
        "created_at",
    )

    inlines = (
        PublicFileInline,
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "sync-public-files/",
                self.admin_site.admin_view(self.sync_public_files_view),
                name="core_publicfileproject_sync",
            ),
        ]
        return custom_urls + urls

    def _can_sync(self, request: HttpRequest) -> bool:
        return request.user.has_perms(
            [
                "core.change_publicfileproject",
                "core.add_publicfile",
            ]
        )

    def sync_public_files_view(self, request: HttpRequest):
        if not self._can_sync(request):
            raise PermissionDenied

        result = None
        if request.method == "POST":
            result = sync_public_files(
                dry_run=request.POST.get("mode") == "dry-run"
            )

        return render(
            request,
            "admin/core/publicfileproject/sync_public_files.html",
            {"result": result},
        )

    @admin.display(description="Archivos")
    def file_count(self, obj):
        return obj.files.count()
