from django.urls import path
from .views import PublicFileUploadView, github_webhook


urlpatterns = [
    path(
        "files/upload/",
        PublicFileUploadView.as_view(),
        name="public-file-upload",
    ),
    path("deploy/webhook/", github_webhook, name="github-webhook"),
]