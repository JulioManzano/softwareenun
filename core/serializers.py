from rest_framework import serializers
from .models import PublicFile


class PublicFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PublicFile
        fields = [
            "id",
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

    def get_url(self, obj):
        request = self.context.get("request")

        if not obj.file:
            return None

        url = obj.file.url

        if request:
            return request.build_absolute_uri(url)

        return url