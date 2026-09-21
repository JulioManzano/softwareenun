from django.test import TestCase

# Create your tests here.
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import PublicFile, PublicFileProject
from .services.public_file_sync import sync_public_files


class PublicFileStorageTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.override_media = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.override_media.enable()
        self.project = PublicFileProject.objects.create(name="Turno Online")

    def tearDown(self):
        self.override_media.disable()
        self.media_directory.cleanup()

    def test_new_file_uses_project_directory(self):
        public_file = PublicFile(project=self.project, name="Logo")
        public_file.file.save("logo.png", ContentFile(b"logo"), save=True)

        self.assertEqual(
            public_file.file.name,
            "public_files/turno-online/logo.png",
        )
        self.assertTrue(Path(self.media_directory.name, public_file.file.name).is_file())

    def test_sync_creates_project_folder(self):
        result = sync_public_files()

        self.assertIn("public_files/turno-online", result.created_directories)
        self.assertTrue(Path(self.media_directory.name, "public_files/turno-online").is_dir())

    def test_sync_imports_manual_file(self):
        file_path = Path(
            self.media_directory.name,
            "public_files",
            self.project.slug,
            "manual.pdf",
        )
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"manual")

        result = sync_public_files()

        public_file = PublicFile.objects.get(file="public_files/turno-online/manual.pdf")
        self.assertEqual(public_file.project, self.project)
        self.assertEqual(public_file.name, "manual.pdf")
        self.assertTrue(public_file.is_public)
        self.assertIn("public_files/turno-online/manual.pdf", result.imported_files)

    def test_sync_is_idempotent(self):
        file_path = Path(
            self.media_directory.name,
            "public_files",
            self.project.slug,
            "manual.pdf",
        )
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"manual")

        first = sync_public_files()
        second = sync_public_files()

        self.assertEqual(len(first.imported_files), 1)
        self.assertEqual(len(second.imported_files), 0)
        self.assertEqual(len(second.existing_files), 1)
        self.assertEqual(PublicFile.objects.count(), 1)

    def test_sync_uses_unique_slugs_for_repeated_names(self):
        second_project = PublicFileProject.objects.create(name="Otro Proyecto")
        for project in (self.project, second_project):
            file_path = Path(
                self.media_directory.name,
                "public_files",
                project.slug,
                "manual.pdf",
            )
            file_path.parent.mkdir(parents=True)
            file_path.write_bytes(b"manual")

        sync_public_files()

        self.assertEqual(
            set(PublicFile.objects.values_list("slug", flat=True)),
            {"manual", "manual-2"},
        )

    def test_sync_detects_missing_file(self):
        public_file = PublicFile.objects.create(
            project=self.project,
            file="public_files/turno-online/missing.pdf",
            name="missing.pdf",
            slug="missing",
        )

        result = sync_public_files()

        self.assertIn(f"{public_file.pk}: public_files/turno-online/missing.pdf", result.missing_records)

    def test_sync_reports_unknown_folder_and_unassigned_file(self):
        unknown_file = Path(
            self.media_directory.name,
            "public_files",
            "unknown-project",
            "file.txt",
        )
        unknown_file.parent.mkdir(parents=True)
        unknown_file.write_bytes(b"unknown")
        unassigned = Path(self.media_directory.name, "direct.txt")
        unassigned.write_bytes(b"unassigned")

        result = sync_public_files()

        self.assertIn("unknown-project", result.unknown_projects)
        self.assertIn("direct.txt", result.unassigned_files)

    def test_dry_run_does_not_create_folder_or_record(self):
        file_path = Path(
            self.media_directory.name,
            "public_files",
            self.project.slug,
            "manual.pdf",
        )
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"manual")

        result = sync_public_files(dry_run=True)

        self.assertEqual(len(result.imported_files), 1)
        self.assertTrue(file_path.is_file())
        self.assertEqual(PublicFile.objects.count(), 0)

    def test_dry_run_command_reports_without_creating_records(self):
        output = StringIO()

        call_command("sync_public_files", "--dry-run", stdout=output)

        self.assertIn("[dry-run]", output.getvalue())
        self.assertEqual(PublicFile.objects.count(), 0)
