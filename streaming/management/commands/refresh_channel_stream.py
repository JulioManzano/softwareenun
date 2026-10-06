from __future__ import annotations

import logging

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from streaming.extractors.base import ExtractionError
from streaming.extractors.elnueve import ElnueveStreamExtractor
from streaming.extractors.telefe import TelefeStreamExtractor
from streaming.services.channel_stream_service import ChannelStreamService

logger = logging.getLogger(__name__)
PREFERRED_CHANNEL_NAMES = {
    "telefe": "Telefe (1080p)",
    "elnueve": "El Nueve (1080p)",
}


class Command(BaseCommand):
    help = "Renueva y guarda la URL de streaming oficial de un Channel."

    def add_arguments(self, parser):
        parser.add_argument("provider", help="Proveedor, por ejemplo: telefe")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Descubre el stream pero no modifica la base de datos.",
        )
        parser.add_argument(
            "--no-playwright",
            action="store_true",
            help="No usar el fallback de navegador.",
        )
        parser.add_argument(
            "--legacy-twitch",
            action="store_true",
            help="Para El Nueve, probar también el canal Twitch legado elnueveenvivo.",
        )

    def handle(self, *args, **options):
        provider = options["provider"].lower().strip()
        if provider not in {"telefe", "elnueve"}:
            raise CommandError("Proveedor no soportado. Actualmente: telefe, elnueve")

        channel = self._find_channel(provider)
        if provider == "telefe":
            extractor = TelefeStreamExtractor(
                use_playwright_fallback=not options["no_playwright"]
            )
        else:
            extractor = ElnueveStreamExtractor(
                use_playwright_fallback=not options["no_playwright"],
                use_legacy_twitch_fallback=options["legacy_twitch"],
            )
        try:
            result = ChannelStreamService(extractor).refresh_channel(
                channel,
                save=not options["dry_run"],
            )
        except ExtractionError as exc:
            logger.exception("No se pudo refrescar el canal %s", provider)
            raise CommandError(str(exc)) from exc

        action = "detectado (dry-run)" if options["dry_run"] else "actualizado"
        self.stdout.write(
            self.style.SUCCESS(
                f"{provider} {action}: hls={result.use_hls} direct={result.link_direct} "
                f"source={result.source}"
            )
        )
        self.stdout.write(
            f"URL: {TelefeStreamExtractor._safe_url_label(result.url)} (query omitida)"
        )
        self.stdout.write(f"Headers: {', '.join(sorted(result.headers)) or 'ninguno'}")
        if result.discovered_from == "Playwright network interception":
            statuses = [
                response["status"]
                for response in result.diagnostics.get("hls_responses", [])
            ]
            self.stdout.write(
                f"Playwright HLS status: {', '.join(statuses) or 'sin respuesta observada'}"
            )

    @staticmethod
    def _find_channel(provider: str):
        model_path = getattr(settings, "CHANNEL_MODEL", "channel.Channel")
        try:
            app_label, model_name = model_path.split(".", 1)
            channel_model = apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as exc:
            raise CommandError(
                "Configurá CHANNEL_MODEL='tu_app.Channel' en settings.py"
            ) from exc

        preferred_name = PREFERRED_CHANNEL_NAMES.get(provider)
        if preferred_name:
            preferred_candidates = channel_model.objects.filter(
                name__iexact=preferred_name
            )
            if preferred_candidates.count() == 1:
                return preferred_candidates.first()

        candidates = channel_model.objects.filter(
            Q(name__iexact=provider) | Q(name__icontains=provider)
        )
        if candidates.count() == 0:
            candidates = channel_model.objects.filter(source__icontains=provider)
        if candidates.count() == 0:
            raise CommandError(f"No se encontró Channel para '{provider}'")
        if candidates.count() > 1:
            names = ", ".join(str(item) for item in candidates[:10])
            raise CommandError(f"Hay varios canales posibles para '{provider}': {names}")
        return candidates.first()
