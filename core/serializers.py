from rest_framework import serializers
from .models import PublicFile


class PublicFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PublicFile
        fields = [
            "id",
            "project",
            "folder",
            "name",
            "file",
            "url",
            "is_public",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "url",
            "created_at",
        ]

    def validate(self, attrs):
        project = attrs.get("project") or getattr(self.instance, "project", None)
        folder = attrs.get("folder") or getattr(self.instance, "folder", None)

        if folder and (not project or folder.project_id != project.id):
            raise serializers.ValidationError(
                "La carpeta debe pertenecer al mismo proyecto."
            )
        if attrs.get("file") and not project:
            raise serializers.ValidationError(
                "Un archivo nuevo requiere un proyecto."
            )

        return attrs

    def get_url(self, obj):
        request = self.context.get("request")

        if not obj.file:
            return None

        url = obj.file.url

        if request:
            return request.build_absolute_uri(url)

        return url
