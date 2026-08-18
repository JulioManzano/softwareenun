from django.urls import path
from .views import PublicFileUploadView


urlpatterns = [
    path(
        "files/upload/",
        PublicFileUploadView.as_view(),
        name="public-file-upload",
    ),
]