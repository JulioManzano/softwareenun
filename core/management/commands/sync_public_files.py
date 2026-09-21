from django.core.management.base import BaseCommand

from core.services.public_file_sync import sync_public_files


class Command(BaseCommand):
    help = "Sincroniza carpetas y registros de PublicFile sin eliminar datos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Informa cambios sin crear carpetas ni registros.",
        )

    def handle(self, *args, **options):
        result = sync_public_files(dry_run=options["dry_run"])
        prefix = "[dry-run] " if result.dry_run else ""

        self.stdout.write(self.style.SUCCESS(f"{prefix}Sincronización finalizada."))
        self.stdout.write(f"Carpetas creadas o a crear: {len(result.created_directories)}")
        self.stdout.write(f"Archivos importados o a importar: {len(result.imported_files)}")
        self.stdout.write(f"Archivos ya existentes: {len(result.existing_files)}")
        self.stdout.write(f"Registros cuyo archivo falta: {len(result.missing_records)}")
        self.stdout.write(f"Proyectos desconocidos: {len(result.unknown_projects)}")
        self.stdout.write(f"Archivos no asignados: {len(result.unassigned_files)}")
        self.stdout.write(f"Errores: {len(result.errors)}")

        for label, values in (
            ("Carpeta", result.created_directories),
            ("Importar", result.imported_files),
            ("Falta", result.missing_records),
            ("Proyecto desconocido", result.unknown_projects),
            ("No asignado", result.unassigned_files),
            ("Error", result.errors),
        ):
            for value in values:
                self.stdout.write(f"  {label}: {value}")
