import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


MAX_DOCUMENT_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PDF_OUTPUT_BYTES = 50 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx"}
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class DocumentConversionError(Exception):
    pass


class UnsupportedDocumentFormat(DocumentConversionError):
    pass


class InvalidDocument(DocumentConversionError):
    pass


class DocumentTooLarge(DocumentConversionError):
    pass


class OutputTooLarge(DocumentConversionError):
    pass


class LibreOfficeUnavailable(DocumentConversionError):
    pass


class ConversionTimedOut(TimeoutError, DocumentConversionError):
    pass


def _validate_document(uploaded_file: UploadedFile) -> str:
    extension = Path(uploaded_file.name or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentFormat(
            "Formato no admitido. Usá .doc, .docx, .xls o .xlsx."
        )

    if uploaded_file.size > MAX_DOCUMENT_UPLOAD_BYTES:
        raise DocumentTooLarge("El archivo supera el máximo permitido de 25 MiB.")

    uploaded_file.seek(0)
    signature = uploaded_file.read(len(OLE_SIGNATURE))
    uploaded_file.seek(0)

    if extension in {".doc", ".xls"}:
        if signature != OLE_SIGNATURE:
            raise InvalidDocument("El archivo no parece ser un documento Office válido.")
        return extension

    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            members = set(archive.namelist())
    except (OSError, zipfile.BadZipFile, ValueError):
        raise InvalidDocument("El archivo no parece ser un documento Office válido.") from None
    finally:
        uploaded_file.seek(0)

    required_member = "word/document.xml" if extension == ".docx" else "xl/workbook.xml"
    if required_member not in members:
        raise InvalidDocument("El contenido del archivo no coincide con su extensión.")
    return extension


def convert_document(uploaded_file: UploadedFile) -> bytes:
    extension = _validate_document(uploaded_file)
    configured_binary = settings.LIBREOFFICE_BIN
    binary = shutil.which(configured_binary)
    if binary is None:
        raise LibreOfficeUnavailable

    timeout = settings.DOCUMENT_CONVERSION_TIMEOUT_SECONDS

    with tempfile.TemporaryDirectory(prefix="multitools-convert-") as temp_directory:
        root = Path(temp_directory)
        input_path = root / f"source{extension}"
        output_directory = root / "output"
        profile_directory = root / "profile"
        output_directory.mkdir()
        profile_directory.mkdir()

        with input_path.open("wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        command = [
            binary,
            "--headless",
            f"-env:UserInstallation={profile_directory.as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_directory),
            str(input_path),
        ]
        environment = {
            "HOME": str(profile_directory),
            "TMPDIR": str(root),
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
        }

        try:
            result = subprocess.run(
                command,
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                check=False,
            )
        except FileNotFoundError:
            raise LibreOfficeUnavailable from None
        except subprocess.TimeoutExpired:
            raise ConversionTimedOut from None

        output_path = output_directory / "source.pdf"
        if result.returncode != 0 or not output_path.is_file():
            raise DocumentConversionError

        output_size = output_path.stat().st_size
        if output_size > MAX_PDF_OUTPUT_BYTES:
            raise OutputTooLarge("El PDF resultante supera el máximo permitido de 50 MiB.")

        with output_path.open("rb") as converted_file:
            pdf_bytes = converted_file.read(MAX_PDF_OUTPUT_BYTES + 1)

        if len(pdf_bytes) > MAX_PDF_OUTPUT_BYTES:
            raise OutputTooLarge("El PDF resultante supera el máximo permitido de 50 MiB.")
        if not pdf_bytes.startswith(b"%PDF-"):
            raise DocumentConversionError

        return pdf_bytes