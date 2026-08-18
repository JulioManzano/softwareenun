from rest_framework import generics
from .models import PublicFile
from .serializers import PublicFileSerializer


class PublicFileUploadView(generics.CreateAPIView):
    queryset = PublicFile.objects.all()
    serializer_class = PublicFileSerializer