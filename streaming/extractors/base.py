from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class ExtractionError(RuntimeError):
    """The official page did not expose a usable stream."""


class DrmDetectedError(ExtractionError):
    """The player appears to require DRM/license negotiation."""


@dataclass(slots=True)
class StreamResult:
    url: str
    use_hls: bool
    link_direct: bool
    headers: dict[str, str] = field(default_factory=dict)
    source: str = ""
    discovered_from: str = ""
    expires_at: datetime | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    playback_type: str = "native"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "use_hls": self.use_hls,
            "link_direct": self.link_direct,
            "headers": dict(self.headers),
            "source": self.source,
            "discovered_from": self.discovered_from,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "diagnostics": dict(self.diagnostics),
            "playback_type": self.playback_type,
        }


class BaseStreamExtractor(ABC):
    @abstractmethod
    def get_stream(self) -> StreamResult:
        raise NotImplementedError
