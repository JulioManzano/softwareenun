from rest_framework import generics
from .models import PublicFile
from .serializers import PublicFileSerializer    
import hashlib
import hmac
import json
import os
import subprocess

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

class PublicFileUploadView(generics.CreateAPIView):
    queryset = PublicFile.objects.all()
    serializer_class = PublicFileSerializer



@csrf_exempt
def github_webhook(request):
    print("=== GITHUB WEBHOOK ===")
    print(f"Method: {request.method}")
    
    ##if request.method != "POST":
    ##    return JsonResponse({"error": "Method not allowed"}, status=405)

    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "").encode()
    signature = request.headers.get("X-Hub-Signature-256", "")

    body = request.body

    expected = "sha256=" + hmac.new(
        secret,
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return JsonResponse({"error": "Invalid signature"}, status=403)

    data = json.loads(body)

    ref = data.get("ref")
    repository = data.get("repository", {}).get("full_name")

    if repository != "JulioManzano/softwareenun":
        return JsonResponse({"error": "Invalid repository"}, status=403)

    if ref != "refs/heads/prod":
        return JsonResponse({"message": "Ignored branch"})

    subprocess.Popen(
        [
            "sudo",
            "/opt/softwareenun/deploy.sh",
        ],
        cwd="/opt/softwareenun",
    )

    return JsonResponse({
        "message": "Deploy started"
    })