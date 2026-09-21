from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils.text import get_valid_filename, slugify

from core.models import PublicFile, PublicFileProject


PUBLIC_FILES_DIRECTORY = "public_files"


@dataclass
class PublicFileSyncResult:
    dry_run: bool = False
    created_directories: list[str] = field(default_factory=list)
    imported_files: list[str] = field(default_factory=list)
    existing_files: list[str] = field(default_factory=list)
    missing_records: list[str] = field(default_factory=list)
    unknown_projects: list[str] = field(default_factory=list)
    unassigned_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _media_root() -> Path:
    return Path(settings.MEDIA_ROOT).resolve()


def _public_files_root() -> Path:
    return _media_root() / PUBLIC_FILES_DIRECTORY


def _relative_name(path: Path) -> str:
    return path.relative_to(_media_root()).as_posix()


def _is_inside(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _safe_display_name(path: Path) -> str:
    return get_valid_filename(path.name) or path.name


def _unique_slug(name: str, used_slugs: set[str]) -> str:
    base = slugify(Path(name).stem) or "file"
    candidate = base[:255]
    suffix = 2
    while candidate in used_slugs or PublicFile.objects.filter(slug=candidate).exists():
        suffix_text = f"-{suffix}"
        candidate = f"{base[:255 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    used_slugs.add(candidate)
    return candidate


def _project_by_slug() -> dict[str, PublicFileProject]:
    return {
        project.slug: project
        for project in PublicFileProject.objects.all()
        if project.slug and slugify(project.slug) == project.slug
    }


def _ensure_project_directories(
    projects: dict[str, PublicFileProject],
    root: Path,
    result: PublicFileSyncResult,
) -> None:
    for slug in sorted(projects):
        directory = root / slug
        if directory.exists():
            if not directory.is_dir():
                result.errors.append(f"La ruta de proyecto no es una carpeta: {directory}")
            continue

        result.created_directories.append(directory.relative_to(_media_root()).as_posix())
        if not result.dry_run:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                result.errors.append(f"No se pudo crear {directory}: {exc}")


def _scan_unknown_media(root: Path, public_root: Path, result: PublicFileSyncResult) -> None:
    if not root.exists():
        return

    for path in root.rglob("*"):
        if not path.is_file() or _is_inside(path, public_root):
            continue
        try:
            result.unassigned_files.append(_relative_name(path))
        except ValueError:
            result.errors.append(f"Archivo fuera de MEDIA_ROOT ignorado: {path}")


def _scan_public_files(
    projects: dict[str, PublicFileProject],
    public_root: Path,
    result: PublicFileSyncResult,
) -> None:
    if not public_root.exists():
        return

    known_paths = {
        str(public_file.file.name).replace("\\", "/")
        for public_file in PublicFile.objects.exclude(file="")
    }
    used_slugs = set(PublicFile.objects.values_list("slug", flat=True))

    for directory in sorted(public_root.iterdir()):
        if not directory.is_dir():
            if directory.is_file():
                result.unassigned_files.append(_relative_name(directory))
            continue

        project = projects.get(directory.name)
        if project is None:
            result.unknown_projects.append(directory.name)
            continue

        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if not _is_inside(path, public_root):
                result.errors.append(f"Archivo fuera de public_files ignorado: {path}")
                continue

            relative_name = _relative_name(path)
            if relative_name in known_paths:
                result.existing_files.append(relative_name)
                continue

            safe_name = _safe_display_name(path)
            if not safe_name:
                result.errors.append(f"Nombre de archivo inválido: {relative_name}")
                continue

            result.imported_files.append(relative_name)
            if result.dry_run:
                continue

            try:
                with transaction.atomic():
                    PublicFile.objects.create(
                        project=project,
                        file=relative_name,
                        name=safe_name,
                        slug=_unique_slug(safe_name, used_slugs),
                        is_public=True,
                    )
                known_paths.add(relative_name)
            except Exception as exc:
                result.errors.append(f"No se pudo importar {relative_name}: {exc}")


def _find_missing_records(result: PublicFileSyncResult) -> None:
    media_root = _media_root()
    for public_file in PublicFile.objects.exclude(file="").select_related("project"):
        relative_name = str(public_file.file.name).replace("\\", "/")
        physical_path = media_root / relative_name
        if not _is_inside(physical_path, media_root) or not physical_path.is_file():
            result.missing_records.append(
                f"{public_file.pk}: {relative_name or '[sin archivo]'}"
            )


def sync_public_files(*, dry_run: bool = False) -> PublicFileSyncResult:
    """Synchronize project directories and physical public files.

    The service only creates directories and missing database records. It never
    deletes or moves files or database rows.
    """
    result = PublicFileSyncResult(dry_run=dry_run)
    media_root = _media_root()
    public_root = _public_files_root()
    projects = _project_by_slug()

    for project in PublicFileProject.objects.all():
        if not project.slug:
            result.errors.append(
                f"El proyecto {project.pk} no tiene slug y no puede tener carpeta."
            )
        elif slugify(project.slug) != project.slug:
            result.errors.append(
                f"El slug del proyecto {project.pk} no es seguro: {project.slug}"
            )

    if not dry_run:
        try:
            public_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            result.errors.append(f"No se pudo crear {public_root}: {exc}")
            return result

    _ensure_project_directories(projects, public_root, result)
    _scan_unknown_media(media_root, public_root, result)
    _scan_public_files(projects, public_root, result)
    _find_missing_records(result)
    return result
