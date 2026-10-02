import io
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from core.views import DocumentToPdfView


@override_settings(ALLOWED_HOSTS=["testserver"])
class DocumentConversionTests(TestCase):
    url = "/api/documents/convert-to-pdf/"

    @staticmethod
    def _authenticate(request):
        request.firebase_claims = {"uid": "document-converter-test"}
        request.user = SimpleNamespace(is_authenticated=True)

    @staticmethod
    def _office_zip(filename, member):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr(member, "<document />")
        return SimpleUploadedFile(filename, buffer.getvalue())

    def test_requires_firebase_authentication(self):
        response = self.client.post(
            self.url,
            {"file": self._office_zip("report.docx", "word/document.xml")},
        )
        self.assertEqual(response.status_code, 401)

    def test_converts_word_and_excel_and_cleans_temporary_files(self):
        input_paths = []

        def run_converter(command, **kwargs):
            self.assertFalse(kwargs["shell"])
            output_directory = Path(command[command.index("--outdir") + 1])
            input_path = Path(command[-1])
            input_paths.append(input_path)
            (output_directory / "source.pdf").write_bytes(b"%PDF-1.7\nconverted")
            return subprocess.CompletedProcess(command, 0, "", "")

        cases = (
            (
                "report.docx",
                lambda: self._office_zip("report.docx", "word/document.xml"),
            ),
            (
                "budget.xlsx",
                lambda: self._office_zip("budget.xlsx", "xl/workbook.xml"),
            ),
            (
                "legacy.doc",
                lambda: SimpleUploadedFile(
                    "legacy.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1office"
                ),
            ),
            (
                "legacy.xls",
                lambda: SimpleUploadedFile(
                    "legacy.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1office"
                ),
            ),
        )
        with (
            patch("core.views.authenticate_request", side_effect=self._authenticate),
            patch("core.services.document_conversion.shutil.which", return_value="/usr/bin/soffice"),
            patch("core.services.document_conversion.subprocess.run", side_effect=run_converter) as run,
        ):
            for filename, make_upload in cases:
                with self.subTest(filename=filename):
                    response = self.client.post(
                        self.url,
                        {"file": make_upload()},
                        HTTP_AUTHORIZATION="Bearer firebase-token",
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response["Content-Type"], "application/pdf")
                    self.assertEqual(response.content, b"%PDF-1.7\nconverted")

        self.assertEqual(run.call_count, 4)
        self.assertTrue(all(not path.exists() for path in input_paths))
        for call in run.call_args_list:
            self.assertFalse(call.kwargs["shell"])
            self.assertIsInstance(call.kwargs["timeout"], int)

    def test_rejects_extension_content_mismatch(self):
        with patch("core.views.authenticate_request", side_effect=self._authenticate):
            response = self.client.post(
                self.url,
                {"file": SimpleUploadedFile("fake.docx", b"not a zip file")},
                HTTP_AUTHORIZATION="Bearer firebase-token",
            )
        self.assertEqual(response.status_code, 422)

    def test_rejects_unsupported_extension(self):
        with patch("core.views.authenticate_request", side_effect=self._authenticate):
            response = self.client.post(
                self.url,
                {"file": SimpleUploadedFile("notes.txt", b"text")},
                HTTP_AUTHORIZATION="Bearer firebase-token",
            )
        self.assertEqual(response.status_code, 415)

    def test_rejects_oversized_file(self):
        with (
            patch("core.views.authenticate_request", side_effect=self._authenticate),
            patch("core.services.document_conversion.MAX_DOCUMENT_UPLOAD_BYTES", 3),
        ):
            response = self.client.post(
                self.url,
                {"file": self._office_zip("report.docx", "word/document.xml")},
                HTTP_AUTHORIZATION="Bearer firebase-token",
            )
        self.assertEqual(response.status_code, 413)

    def test_rejects_oversized_request_before_parsing_multipart(self):
        request = RequestFactory().post(
            self.url,
            data=b"",
            content_type="multipart/form-data",
            HTTP_AUTHORIZATION="Bearer firebase-token",
        )
        request.META["CONTENT_LENGTH"] = str(1024 * 1024 + 2)

        with (
            patch("core.views.authenticate_request", side_effect=self._authenticate),
            patch("core.views.MAX_DOCUMENT_UPLOAD_BYTES", 1),
        ):
            response = DocumentToPdfView.as_view()(request)

        self.assertEqual(response.status_code, 413)

    def test_conversion_timeout_returns_gateway_timeout_and_cleans_temporary_files(self):
        input_paths = []

        def timeout(command, **kwargs):
            input_paths.append(Path(command[-1]))
            raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

        with (
            patch("core.views.authenticate_request", side_effect=self._authenticate),
            patch("core.services.document_conversion.shutil.which", return_value="/usr/bin/soffice"),
            patch("core.services.document_conversion.subprocess.run", side_effect=timeout),
        ):
            response = self.client.post(
                self.url,
                {"file": self._office_zip("report.docx", "word/document.xml")},
                HTTP_AUTHORIZATION="Bearer firebase-token",
            )

        self.assertEqual(response.status_code, 504)
        self.assertTrue(input_paths)
        self.assertFalse(input_paths[0].exists())