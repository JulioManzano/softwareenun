from django.urls import path
from .views import DocumentToPdfView, PublicFileUploadView, github_webhook


urlpatterns = [
    path(
        "files/upload/",
        PublicFileUploadView.as_view(),
        name="public-file-upload",
    ),
    path(
        "documents/convert-to-pdf/",
        DocumentToPdfView.as_view(),
        name="document-to-pdf",
    ),
    path("deploy/webhook/", github_webhook, name="github-webhook"),
]