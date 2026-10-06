from __future__ import annotations

import logging
from typing import Any

from streaming.extractors.base import StreamResult

logger = logging.getLogger(__name__)


class ChannelStreamService:
    """Connects discovery with the existing Channel persistence model."""

    def __init__(self, extractor: Any):
        self.extractor = extractor

    def refresh_channel(self, channel: Any, *, save: bool = True) -> StreamResult:
        result = self.extractor.get_stream()
        channel.url = result.url
        channel.use_hls = result.use_hls
        channel.link_direct = result.link_direct
        channel.headers = result.headers
        channel.source = result.source
        if save:
            channel.save(
                update_fields=[
                    "url",
                    "use_hls",
                    "link_direct",
                    "headers",
                    "source",
                    "updated_at",
                ]
            )
        logger.info(
            "Channel stream refreshed channel_id=%s name=%s source=%s hls=%s direct=%s",
            getattr(channel, "pk", None),
            getattr(channel, "name", None),
            result.source,
            result.use_hls,
            result.link_direct,
        )
        return result
