from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from .base import BaseStreamExtractor, DrmDetectedError, ExtractionError, StreamResult

logger = logging.getLogger(__name__)


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.iframes: list[str] = []
        self.scripts: list[str] = []
        self._in_script = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "iframe" and values.get("src"):
            self.iframes.append(values["src"] or "")
        if tag.lower() == "script":
            self._in_script = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_script:
            self.scripts.append("".join(self._parts))
            self._in_script = False
            self._parts = []


class ElnueveStreamExtractor(BaseStreamExtractor):
    """Discover El Nueve's current official live stream.

    The current page embeds YouTube. Older versions of the page used Twitch,
    so the Twitch GQL path remains available as an explicit legacy fallback.
    Temporary tokens are requested at runtime and never hardcoded.
    """

    LANDING_URL = "https://www.elnueve.com.ar/en-vivo"
    TWITCH_GQL_URL = "https://gql.twitch.tv/gql"
    TWITCH_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
    TWITCH_QUERY_HASH = "ed230aa1e33e07eebb8928504583da78a5173989fadfb1ac94be06a04f3cdbe9"
    LEGACY_TWITCH_CHANNEL = "elnueveenvivo"
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        *,
        landing_url: str | None = None,
        timeout: float = 20.0,
        use_playwright_fallback: bool = True,
        use_legacy_twitch_fallback: bool = False,
    ) -> None:
        self.landing_url = landing_url or self.LANDING_URL
        self.timeout = timeout
        self.use_playwright_fallback = use_playwright_fallback
        self.use_legacy_twitch_fallback = use_legacy_twitch_fallback

    def get_stream(self) -> StreamResult:
        httpx = self._httpx()
        page_html = ""
        iframe_url = ""
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self.USER_AGENT},
            ) as client:
                response = client.get(self.landing_url)
                response.raise_for_status()
                page_html = response.text
                iframe_url = self._find_provider_iframe(page_html) or ""
                direct_hls = self._find_hls(page_html)
                logger.info(
                    "El Nueve landing loaded status=%s bytes=%s iframe=%s hls_in_html=%s",
                    response.status_code,
                    len(page_html),
                    iframe_url or "none",
                    bool(direct_hls),
                )

                if direct_hls:
                    return self._result_from_hls(
                        client,
                        direct_hls,
                        source="El Nueve / official page HLS",
                        discovered_from="official page HTML",
                    )

                twitch_channel = self._find_twitch_channel(page_html)
                if twitch_channel:
                    return self._discover_twitch(client, twitch_channel)

                # This is useful for deployments where the page changes back
                # to Twitch without requiring a code change, but it is off by
                # default because the current page is YouTube.
                if self.use_legacy_twitch_fallback:
                    return self._discover_twitch(client, self.LEGACY_TWITCH_CHANNEL)
        except DrmDetectedError:
            raise
        except Exception as exc:
            logger.warning("El Nueve HTTP discovery failed: %s", exc, exc_info=True)

        if self.use_playwright_fallback:
            return self._discover_playwright(known_iframe=iframe_url)
        raise ExtractionError(
            "El Nueve actualmente expone un reproductor dinámico y no se encontró "
            "una URL HLS usando HTTP"
        )

    def _discover_twitch(self, client: Any, channel: str) -> StreamResult:
        origin = self._origin(self.landing_url)
        payload = [
            {
                "operationName": "PlaybackAccessToken",
                "variables": {
                    "isLive": True,
                    "login": channel,
                    "isVod": False,
                    "vodID": "",
                    "playerType": "embed",
                    "platform": "web",
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": self.TWITCH_QUERY_HASH,
                    }
                },
            }
        ]
        response = client.post(
            self.TWITCH_GQL_URL,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Client-ID": self.TWITCH_CLIENT_ID,
                "Origin": origin,
                "Referer": self.landing_url,
            },
        )
        response.raise_for_status()
        try:
            data = response.json()
            token_data = data[0]["data"]["streamPlaybackAccessToken"]
            token = token_data["value"]
            signature = token_data["signature"]
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExtractionError("Twitch no devolvió PlaybackAccessToken válido") from exc

        hls_url = (
            f"https://usher.ttvnw.net/api/channel/hls/{channel}.m3u8?"
            + urlencode(
                {
                    "sig": signature,
                    "token": token,
                    "allow_source": "true",
                    "player": "twitchweb",
                }
            )
        )
        result = self._result_from_hls(
            client,
            hls_url,
            source="El Nueve / Twitch",
            discovered_from="Twitch GQL PlaybackAccessToken",
            headers={},
        )
        result.diagnostics.update(
            twitch_channel=channel,
            token_source="gql.twitch.tv/gql",
            token_persisted=False,
        )
        return result

    def _discover_playwright(self, *, known_iframe: str = "") -> StreamResult:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ExtractionError(
                "El Nueve requiere Playwright para inspeccionar el iframe dinámico. "
                "Instalá playwright y ejecutá: playwright install chromium"
            ) from exc

        hls_requests: list[dict[str, Any]] = []
        json_hls: list[dict[str, Any]] = []
        observed_urls: list[str] = []

        def headers_for(request: Any) -> dict[str, str]:
            try:
                return dict(request.all_headers())
            except Exception:
                return dict(request.headers)

        def on_request(request: Any) -> None:
            observed_urls.append(request.url)
            if self._is_hls(request.url):
                item = {"url": request.url, "headers": headers_for(request)}
                hls_requests.append(item)
                logger.info("El Nueve Playwright HLS request url=%s", request.url)

        def on_response(response: Any) -> None:
            url = response.url
            if not self._is_json_response(response) and "youtubei" not in url:
                return
            try:
                body = response.body().decode("utf-8", "replace")
            except Exception:
                return
            hls_url = self._find_hls(body)
            if hls_url:
                item = {
                    "url": hls_url,
                    "headers": headers_for(response.request),
                    "response_url": url,
                }
                json_hls.append(item)
                logger.info("El Nueve HLS found in JSON response url=%s", url)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.USER_AGENT)
            page = context.new_page()
            page.on("request", on_request)
            page.on("response", on_response)
            try:
                page.goto(
                    self.landing_url,
                    wait_until="domcontentloaded",
                    timeout=int(self.timeout * 1000),
                )
                page.wait_for_timeout(15_000)
                body_text = page.locator("body").inner_text(timeout=5_000)
                if self._looks_like_drm(observed_urls, body_text):
                    raise DrmDetectedError(
                        "El reproductor de El Nueve parece usar DRM/license negotiation; "
                        "no se intenta evadirlo."
                    )

                candidates = hls_requests + json_hls
                if not candidates:
                    provider = "YouTube" if "youtube.com/embed" in known_iframe else "dinámico"
                    raise ExtractionError(
                        f"El reproductor oficial de El Nueve ({provider}) no expuso una URL HLS"
                    )
                selected = candidates[-1]
                return StreamResult(
                    url=selected["url"],
                    use_hls=True,
                    link_direct=True,
                    headers=self._select_headers(selected["headers"]),
                    source="El Nueve / official player HLS",
                    discovered_from="Playwright network interception",
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
                    diagnostics={
                        "fallback": "playwright",
                        "known_iframe": known_iframe,
                        "hls_requests": len(hls_requests),
                        "json_hls_matches": len(json_hls),
                        "token_persisted": False,
                    },
                )
            except PlaywrightTimeoutError as exc:
                raise ExtractionError("Timeout esperando el reproductor de El Nueve") from exc
            finally:
                context.close()
                browser.close()

    def _result_from_hls(
        self,
        client: Any,
        hls_url: str,
        *,
        source: str,
        discovered_from: str,
        headers: dict[str, str] | None = None,
    ) -> StreamResult:
        playback_headers = headers or {}
        response = client.get(
            hls_url,
            headers={
                **playback_headers,
                "Accept": "application/vnd.apple.mpegurl, application/x-mpegURL, */*",
            },
        )
        content = response.text[:20_000]
        if response.status_code >= 400:
            raise ExtractionError(f"La playlist de El Nueve respondió HTTP {response.status_code}")
        if "#EXTM3U" not in content:
            raise ExtractionError("La respuesta de El Nueve no contiene un manifest HLS")
        return StreamResult(
            url=hls_url,
            use_hls=True,
            link_direct=True,
            headers=playback_headers,
            source=source,
            discovered_from=discovered_from,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            diagnostics={
                "manifest_status": response.status_code,
                "manifest_kind": "master" if "#EXT-X-STREAM-INF" in content else "media",
                "token_persisted": False,
            },
        )

    def _httpx(self):
        try:
            import httpx
        except ImportError as exc:
            raise ExtractionError("Instalá httpx: pip install httpx") from exc
        return httpx

    @staticmethod
    def _find_provider_iframe(html: str) -> str | None:
        matches = re.findall(
            r"<iframe[^>]+src=[\"']([^\"']+)[\"']",
            html,
            flags=re.IGNORECASE,
        )
        for src in matches:
            if any(host in src.lower() for host in ("youtube.com/embed", "youtube-nocookie.com/embed", "twitch.tv")):
                return src
        return matches[0] if matches else None

    @staticmethod
    def _find_twitch_channel(html: str) -> str | None:
        patterns = (
            r"twitch\.tv/(?!videos/|directory/|search\?)([a-z0-9_]+)",
            r"(?:channel|login)\s*[=:]\s*[\"']([a-z0-9_]+)[\"']",
        )
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _find_hls(text: str) -> str | None:
        candidates = re.findall(
            r"https?://[^\"'\\\s<>]+\.m3u8(?:\?[^\"'\\\s<>]+)?",
            text,
            flags=re.IGNORECASE,
        )
        return candidates[0] if candidates else None

    @staticmethod
    def _is_hls(url: str) -> bool:
        return bool(re.search(r"\.m3u8(?:$|[?#])", url, flags=re.IGNORECASE))

    @staticmethod
    def _origin(url: str) -> str:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    @staticmethod
    def _is_json_response(response: Any) -> bool:
        return "json" in response.headers.get("content-type", "").lower()

    @staticmethod
    def _select_headers(headers: dict[str, str]) -> dict[str, str]:
        accepted = {"referer", "origin", "user-agent", "authorization", "cookie", "x-api-token"}
        result = {}
        for key, value in headers.items():
            if key.lower() in accepted and value:
                result["X-API-Token" if key.lower() == "x-api-token" else key.title()] = value
        return result

    @staticmethod
    def _looks_like_drm(urls: list[str], body_text: str) -> bool:
        observed = " ".join(urls + [body_text]).lower()
        return any(marker in observed for marker in ("widevine", "fairplay", "playready", "clearkey", ".mpd", "license"))
