"""Structured Event schemas and in-process asyncio pub/sub bus."""
from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Awaitable, Callable, Dict, List


@dataclass
class MeetingEvent:
      event_id: str
      timestamp: float
      event_type: str
      source_region: str
      payload: Dict[str, Any]
      confidence: float
      content_hash: str
      window_hwnd: int = 0

    @staticmethod
    def create(
              event_type: str,
              source_region: str,
              payload: Dict[str, Any],
              confidence: float = 0.95,
              window_hwnd: int = 0,
    ) -> "MeetingEvent":
              raw = f"{event_type}:{source_region}:{sorted(payload.items())}"
              content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
              return MeetingEvent(
                  event_id=f"evt_{uuid.uuid4().hex[:12]}",
                  timestamp=time.time(),
                  event_type=event_type,
                  source_region=source_region,
                  payload=payload,
                  confidence=confidence,
                  content_hash=content_hash,
                  window_hwnd=window_hwnd,
              )

    def to_dict(self) -> Dict[str, Any]:
              return asdict(self)


Subscriber = Callable[[MeetingEvent], Awaitable[None]]


class EventBus:
      """In-process asynchronous event bus."""

    def __init__(self) -> None:
              self._subscribers: List[Subscriber] = []
              self.history: List[MeetingEvent] = []

    def subscribe(self, callback: Subscriber) -> None:
              self._subscribers.append(callback)

    async def publish(self, event: MeetingEvent) -> None:
              self.history.append(event)
              if len(self.history) > 500:
                            self.history = self.history[-500:]
                        for sub in self._subscribers:
                                      await sub(event)
