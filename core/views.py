from rest_framework import generics
from .models import PublicFile
from .serializers import PublicFileSerializer    
from django.core.exceptions import RequestDataTooBig
from django.http import HttpResponse, JsonResponse
from django.http.multipartparser import MultiPartParserError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .services.document_conversion import (
    DocumentConversionError,
    DocumentTooLarge,
    LibreOfficeUnavailable,
    MAX_DOCUMENT_UPLOAD_BYTES,
    OutputTooLarge,
    UnsupportedDocumentFormat,
    convert_document,
)
from .services.firebase_auth import authenticate_request, FirebaseAuthenticationError
import hashlib
import hmac
import json
import os
import subprocess


@method_decorator(csrf_exempt, name="dispatch")
class DocumentToPdfView(View):
    def post(self, request):
        try:
            authenticate_request(request)
        except FirebaseAuthenticationError:
            return JsonResponse({"error": "La sesión no es válida o expiró."}, status=401)

        if not getattr(request, "firebase_claims", None) or not request.user.is_authenticated:
            return JsonResponse({"error": "Iniciá sesión para convertir documentos."}, status=401)

        try:
            content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            return JsonResponse({"error": "El tamaño de la solicitud no es válido."}, status=400)
        if content_length > MAX_DOCUMENT_UPLOAD_BYTES + 1024 * 1024:
            return JsonResponse({"error": "El archivo supera el máximo permitido de 25 MiB."}, status=413)

        try:
            files = request.FILES.getlist("file")
        except RequestDataTooBig:
            return JsonResponse({"error": "El archivo supera el máximo permitido de 25 MiB."}, status=413)
        except MultiPartParserError:
            return JsonResponse({"error": "La solicitud multipart no es válida."}, status=400)

        if len(files) != 1 or len(request.FILES) != 1:
            return JsonResponse({"error": "Seleccioná un único archivo para convertir."}, status=400)

        try:
            pdf_bytes = convert_document(files[0])
        except UnsupportedDocumentFormat as exc:
            return JsonResponse({"error": str(exc)}, status=415)
        except DocumentTooLarge as exc:
            return JsonResponse({"error": str(exc)}, status=413)
        except LibreOfficeUnavailable:
            return JsonResponse(
                {"error": "El servicio de conversión no está disponible."},
                status=503,
            )
        except TimeoutError:
            return JsonResponse(
                {"error": "La conversión superó el tiempo límite. Probá con un archivo más pequeño."},
                status=504,
            )
        except OutputTooLarge as exc:
            return JsonResponse({"error": str(exc)}, status=422)
        except DocumentConversionError:
            return JsonResponse(
                {"error": "No se pudo convertir el documento. Verificá que no esté dañado o protegido."},
                status=422,
            )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="converted.pdf"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

class PublicFileUploadView(generics.CreateAPIView):
    queryset = PublicFile.objects.all()
    serializer_class = PublicFileSerializer



@csrf_exempt
def github_webhook2(request):
    print("=== GITHUB WEBHOOK 1 ===")
    print(f"Method: {request.method}")

    print("🚀 Iniciando deploy...")

    subprocess.Popen(
        [
            "/opt/softwareenun/deploy.sh",
        ],
        cwd="/opt/softwareenun",
    )

    print("✅ Deploy enviado al proceso")

    return JsonResponse({
        "message": "Deploy started"
    })
    
@csrf_exempt
def github_webhook(request):
    print("=== GITHUB WEBHOOK 2 ===")
    print(f"Method: {request.method}")
    
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

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