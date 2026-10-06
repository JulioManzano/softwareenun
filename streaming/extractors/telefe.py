from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .base import BaseStreamExtractor, DrmDetectedError, ExtractionError, StreamResult

logger = logging.getLogger(__name__)


class _ScriptParser(HTMLParser):
    """Small dependency-free parser used to collect script and iframe content."""

    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self.iframes: list[str] = []
        self._in_script = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag.lower() == "script":
            self._in_script = True
            self._script_parts = []
        elif tag.lower() == "iframe" and attrs_dict.get("src"):
            self.iframes.append(attrs_dict["src"] or "")

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_script:
            self.scripts.append("".join(self._script_parts))
            self._in_script = False
            self._script_parts = []


@dataclass(slots=True)
class _Discovery:
    landing_url: str
    lambda_url: str
    stream_id: str
    access_token: str
    player_id: str
    iframe_url: str
    hls_url: str
    headers: dict[str, str]
    diagnostics: dict[str, Any]


class TelefeStreamExtractor(BaseStreamExtractor):
    """Discover Telefe's current official Mediastream HLS URL.

    The extractor deliberately obtains a new Lambda token on every call. It
    never stores a token as a constant and never proxies media or downloads
    segments. ``httpx`` is the preferred path; Playwright is optional and is
    used only when the provider changes the browser-only part of the flow.
    """

    LANDING_URL = "https://www.mitelefe.com/telefe-en-vivo"
    SOURCE = "Mi Telefe / Mediastream"
    DEFAULT_TIMEOUT = 20.0
    PLAYER_WAIT_SECONDS = 15_000
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        *,
        landing_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        use_playwright_fallback: bool = True,
        logger_: logging.Logger | None = None,
    ) -> None:
        self.landing_url = landing_url or self.LANDING_URL
        self.timeout = timeout
        self.use_playwright_fallback = use_playwright_fallback
        self.logger = logger_ or logger

    def get_stream(self) -> StreamResult:
        try:
            discovery = self._discover_httpx()
            return StreamResult(
                url=discovery.hls_url,
                use_hls=True,
                link_direct=True,
                headers=discovery.headers,
                source=self.SOURCE,
                discovered_from="lambda -> mdstrm iframe -> MDSTRM.OPTIONS.src.hls",
                # The page itself caches the token for 25 minutes. This is a
                # conservative operational hint, not a token claim from the
                # provider.
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
                diagnostics=discovery.diagnostics,
            )
        except DrmDetectedError:
            raise
        except Exception as exc:
            self.logger.warning("Telefe HTTP discovery failed: %s", exc, exc_info=True)

        if self.use_playwright_fallback:
            return self._discover_playwright()
        raise ExtractionError("No se pudo descubrir el stream de Telefe con HTTP")

    def _httpx(self):
        try:
            import httpx
        except ImportError as exc:
            raise ExtractionError(
                "Instalá httpx para el extractor HTTP: pip install httpx"
            ) from exc
        return httpx

    def _discover_httpx(self) -> _Discovery:
        httpx = self._httpx()
        origin = self._origin(self.landing_url)
        base_headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers=base_headers,
        ) as client:
            landing_response = client.get(self.landing_url)
            landing_response.raise_for_status()
            landing_html = landing_response.text
            lambda_url, stream_id = self._parse_landing(landing_html)
            self.logger.info(
                "Telefe landing loaded status=%s bytes=%s lambda=%s stream_id=%s",
                landing_response.status_code,
                len(landing_html),
                lambda_url,
                stream_id,
            )

            lambda_response = client.get(
                self._with_query(lambda_url, {"stream_id": stream_id}),
                headers={
                    "Accept": "application/json",
                    "Referer": self.landing_url,
                    "Origin": origin,
                },
            )
            lambda_response.raise_for_status()
            payload = self._json_object(lambda_response.text, "Lambda")
            access_token = str(payload.get("access_token") or "")
            resolved_stream_id = str(payload.get("stream_id") or stream_id)
            player_id = str(payload.get("player_id") or "")
            if not access_token or not player_id:
                raise ExtractionError("La Lambda no devolvió access_token/player_id")

            iframe_url = (
                f"https://mdstrm.com/live-stream/{resolved_stream_id}?"
                + urlencode({"player": player_id, "access_token": access_token})
            )
            iframe_response = client.get(
                iframe_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "Referer": self.landing_url,
                    "Origin": origin,
                },
            )
            iframe_response.raise_for_status()
            iframe_html = iframe_response.text
            hls_url = self._parse_hls_from_player(iframe_html)
            if not hls_url:
                raise ExtractionError("El iframe no expuso una URL HLS")

            playback_headers = {
                "Referer": self.landing_url,
                "Origin": origin,
                "User-Agent": self.USER_AGENT,
            }
            cookie_header = self._cookie_header(client)
            if cookie_header:
                playback_headers["Cookie"] = cookie_header

            diagnostics: dict[str, Any] = {
                "landing_status": landing_response.status_code,
                "lambda_status": lambda_response.status_code,
                "iframe_status": iframe_response.status_code,
                "lambda_url": lambda_url,
                "stream_id": resolved_stream_id,
                "player_id": player_id,
                "iframe_url": self._redact_url(iframe_url),
                "token_source": "lambda_response",
                "token_persisted": False,
            }
            manifest_status, manifest_kind = self._verify_manifest(
                client, hls_url, playback_headers
            )
            diagnostics.update(
                manifest_status=manifest_status,
                manifest_kind=manifest_kind,
                cookie_forwarded=bool(cookie_header),
            )
            self.logger.info(
                "Telefe HLS discovered status=%s kind=%s cookie_forwarded=%s url=%s",
                manifest_status,
                manifest_kind,
                bool(cookie_header),
                hls_url,
            )
            return _Discovery(
                landing_url=self.landing_url,
                lambda_url=lambda_url,
                stream_id=resolved_stream_id,
                access_token=access_token,
                player_id=player_id,
                iframe_url=iframe_url,
                hls_url=hls_url,
                headers=playback_headers,
                diagnostics=diagnostics,
            )

    def _discover_playwright(self) -> StreamResult:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ExtractionError(
                "HTTP no pudo descubrir el stream y Playwright no está instalado. "
                "Instalá playwright y ejecutá: playwright install chromium"
            ) from exc

        requests: list[dict[str, Any]] = []
        responses: list[dict[str, Any]] = []
        hls_responses: list[dict[str, str]] = []
        failed_requests: list[dict[str, str]] = []
        page_errors: list[str] = []
        console_errors: list[str] = []

        def capture_request(request: Any) -> None:
            url = request.url
            if self._is_hls_url(url):
                try:
                    headers = dict(request.all_headers())
                except Exception:
                    headers = dict(request.headers)
                requests.append({"url": url, "headers": headers})
                self.logger.info(
                    "Playwright HLS request resource=%s",
                    self._safe_url_label(url),
                )

        def capture_response(response: Any) -> None:
            url = response.url
            is_hls = self._is_hls_url(url)
            if is_hls or self._looks_like_json(response.headers):
                response_info = {
                    "url": self._safe_url_label(url),
                    "status": str(response.status),
                    "content_type": response.headers.get("content-type", "")[:80],
                }
                responses.append(response_info)
                if is_hls:
                    hls_responses.append(response_info)

        def capture_failed_request(request: Any) -> None:
            failure = request.failure or "unknown"
            failed_requests.append(
                {
                    "resource": self._safe_url_label(request.url),
                    "failure": self._safe_diagnostic_text(str(failure)),
                }
            )

        def capture_page_error(error: Any) -> None:
            page_errors.append(self._safe_diagnostic_text(str(error)))

        def capture_console(message: Any) -> None:
            if message.type == "error":
                console_errors.append(self._safe_diagnostic_text(message.text))

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.USER_AGENT)
            page = context.new_page()
            page.on("request", capture_request)
            page.on("response", capture_response)
            page.on("requestfailed", capture_failed_request)
            page.on("pageerror", capture_page_error)
            page.on("console", capture_console)
            try:
                navigation_response = page.goto(
                    self.landing_url,
                    wait_until="domcontentloaded",
                    timeout=int(self.timeout * 1000),
                )
                page.wait_for_timeout(self.PLAYER_WAIT_SECONDS)
                body_text = page.locator("body").inner_text(timeout=5_000)
                if self._looks_like_drm(page, requests, responses, body_text):
                    raise DrmDetectedError(
                        "El reproductor parece usar DRM/license negotiation; no se intenta evadirlo."
                    )
                if not requests:
                    frames = [
                        self._safe_url_label(frame.url)
                        for frame in page.frames
                        if frame.url
                    ]
                    self.logger.warning(
                        "Telefe Playwright no observó HLS navigation_status=%s "
                        "title=%r frames=%s responses=%s failed_requests=%s "
                        "page_errors=%s console_errors=%s",
                        navigation_response.status if navigation_response else None,
                        self._safe_diagnostic_text(page.title()),
                        frames[:10],
                        responses[-10:],
                        failed_requests[-10:],
                        page_errors[-5:],
                        console_errors[-10:],
                    )
                    raise ExtractionError(
                        "Playwright no observó una request .m3u8 en el reproductor oficial"
                    )
                selected = requests[-1]
                headers = self._select_playback_headers(selected["headers"])
                return StreamResult(
                    url=selected["url"],
                    use_hls=True,
                    link_direct=True,
                    headers=headers,
                    source=self.SOURCE,
                    discovered_from="Playwright network interception",
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
                    diagnostics={
                        "fallback": "playwright",
                        "hls_requests": len(requests),
                        "hls_responses": hls_responses[-10:],
                        "failed_requests": failed_requests[-10:],
                        "page_errors": page_errors[-5:],
                        "console_errors": console_errors[-10:],
                        "request_headers": sorted(headers),
                    },
                )
            except PlaywrightTimeoutError as exc:
                raise ExtractionError("Timeout esperando el reproductor de Telefe") from exc
            finally:
                context.close()
                browser.close()

    def _parse_landing(self, html: str) -> tuple[str, str]:
        parser = _ScriptParser()
        parser.feed(html)
        all_scripts = "\n".join(parser.scripts)
        lambda_match = re.search(
            r"LAMBDA_URL\s*=\s*[\"'](?P<url>https?://[^\"']+)[\"']",
            all_scripts,
        )
        stream_match = re.search(
            r"STREAM_ID\s*=\s*[\"'](?P<id>[A-Za-z0-9_-]+)[\"']",
            all_scripts,
        )
        if not lambda_match or not stream_match:
            raise ExtractionError(
                "No se encontraron LAMBDA_URL y STREAM_ID en los scripts de Telefe"
            )
        return lambda_match.group("url"), stream_match.group("id")

    def _parse_hls_from_player(self, html: str) -> str | None:
        parser = _ScriptParser()
        parser.feed(html)
        script_text = "\n".join(parser.scripts)
        marker = re.search(r"window\.MDSTRM\.OPTIONS\s*=\s*", script_text)
        if marker:
            start = script_text.find("{", marker.end())
            if start >= 0:
                try:
                    value, _ = json.JSONDecoder().raw_decode(script_text[start:])
                    hls = value.get("src", {}).get("hls") if isinstance(value, dict) else None
                    if isinstance(hls, str) and self._is_hls_url(hls):
                        return hls
                except json.JSONDecodeError:
                    self.logger.warning("No se pudo parsear MDSTRM.OPTIONS como JSON")

        candidates = re.findall(
            r"https?://[^\"'\\\s<>]+\.m3u8(?:\?[^\"'\\\s<>]+)?",
            html,
            flags=re.IGNORECASE,
        )
        return candidates[0] if candidates else None

    def _verify_manifest(
        self,
        client: Any,
        hls_url: str,
        headers: dict[str, str],
    ) -> tuple[int, str]:
        response = client.get(
            hls_url,
            headers={
                **headers,
                "Accept": "application/vnd.apple.mpegurl, application/x-mpegURL, */*",
            },
        )
        content = response.text[:20_000]
        if response.status_code >= 400:
            raise ExtractionError(
                f"La playlist HLS respondió HTTP {response.status_code}: "
                f"{self._safe_response_text(content)}"
            )
        if "#EXTM3U" not in content:
            raise ExtractionError("La respuesta del manifest no contiene #EXTM3U")
        kind = "master" if "#EXT-X-STREAM-INF" in content else "media"
        return response.status_code, kind

    def _cookie_header(self, client: Any) -> str:
        try:
            return "; ".join(f"{cookie.name}={cookie.value}" for cookie in client.cookies.jar)
        except Exception:
            return ""

    def _json_object(self, text: str, label: str) -> dict[str, Any]:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"{label} no devolvió JSON válido") from exc
        if not isinstance(value, dict):
            raise ExtractionError(f"{label} no devolvió un objeto JSON")
        return value

    @staticmethod
    def _origin(url: str) -> str:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    @staticmethod
    def _with_query(url: str, values: dict[str, str]) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query.update(values)
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    @staticmethod
    def _is_hls_url(url: str) -> bool:
        return bool(re.search(r"\.m3u8(?:$|[?#])", url, flags=re.IGNORECASE))

    @staticmethod
    def _looks_like_json(headers: dict[str, str]) -> bool:
        content_type = headers.get("content-type", "").lower()
        return "json" in content_type

    @staticmethod
    def _select_playback_headers(headers: dict[str, str]) -> dict[str, str]:
        wanted = {"referer", "origin", "user-agent", "authorization", "cookie", "x-api-token"}
        return {
            key.title() if key.lower() != "x-api-token" else "X-API-Token": value
            for key, value in headers.items()
            if key.lower() in wanted and value
        }

    @staticmethod
    def _looks_like_drm(page: Any, requests: list[dict[str, Any]], responses: list[dict[str, Any]], body_text: str) -> bool:
        observed = " ".join(
            [body_text, *(item["url"] for item in requests), *(item["url"] for item in responses)]
        ).lower()
        drm_markers = ("widevine", "fairplay", "playready", "license", ".mpd", "clearkey")
        return any(marker in observed for marker in drm_markers)

    @staticmethod
    def _safe_response_text(text: str) -> str:
        # Avoid logging a whole provider error or any accidental token.
        return re.sub(r"(access_token|token|hdnea)=([^&\s]+)", r"\1=<redacted>", text, flags=re.I)[:300]

    @staticmethod
    def _safe_url_label(url: str) -> str:
        parsed = urlparse(url)
        resource_type = next(
            (
                extension
                for extension in (".m3u8", ".mpd", ".js", ".json", ".html")
                if parsed.path.lower().endswith(extension)
            ),
            "",
        )
        if parsed.hostname:
            return f"{parsed.scheme}://{parsed.hostname}/...{resource_type}"
        return parsed.scheme or "<unknown>"

    @classmethod
    def _safe_diagnostic_text(cls, text: str) -> str:
        text = re.sub(
            r"https?://[^\s\"'<>]+",
            lambda match: cls._safe_url_label(match.group()),
            text,
        )
        text = re.sub(
            r"(?i)\b(cookie|authorization|x-api-token)\s*[:=]\s*[^,;\s]+",
            r"\1=<redacted>",
            text,
        )
        return cls._safe_response_text(text)

    @staticmethod
    def _redact_url(url: str) -> str:
        parsed = urlparse(url)
        return urlunparse(parsed._replace(query=""))
