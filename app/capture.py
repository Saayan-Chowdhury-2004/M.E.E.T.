"""HWND-isolated screen capture (Windows Graphics Capture with MSS fallback) + 60s RAM Ring Buffer."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

import numpy as np

from app.dpi import Rect
from app.meeting_tracker import MeetingWindowInfo


@dataclass
class CapturedFrame:
      timestamp: float
      hwnd: int
      rect: Rect
      pixels: np.ndarray
      backend: str


class FrameRingBuffer:
      """Ephemeral RAM ring buffer that automatically evicts frames older than `max_age_seconds`."""

    def __init__(self, max_age_seconds: float = 60.0, max_frames: int = 240) -> None:
              self.max_age_seconds = max_age_seconds
              self.max_frames = max_frames
              self._buffer: Deque[CapturedFrame] = deque()

    def push(self, frame: CapturedFrame) -> None:
              self._buffer.append(frame)
              self.evict_expired(now=frame.timestamp)
              while len(self._buffer) > self.max_frames:
                            self._buffer.popleft()

          def evict_expired(self, now: Optional[float] = None) -> int:
                    current = now if now is not None else time.time()
                    removed = 0
                    while self._buffer and (current - self._buffer[0].timestamp) > self.max_age_seconds:
                                  self._buffer.popleft()
                                  removed += 1
                              return removed

    def latest(self) -> Optional[CapturedFrame]:
              self.evict_expired()
        return self._buffer[-1] if self._buffer else None

    def __len__(self) -> int:
              self.evict_expired()
        return len(self._buffer)


class WindowCaptureEngine:
      """Captures only the target meeting window surface."""

    def __init__(self, preferred_backend: str = "auto", ring_buffer_seconds: float = 60.0) -> None:
              self.preferred_backend = preferred_backend
        self.ring_buffer = FrameRingBuffer(max_age_seconds=ring_buffer_seconds)
        self._synthetic_frame: Optional[np.ndarray] = None

    def set_synthetic_frame(self, pixels: np.ndarray) -> None:
              self._synthetic_frame = pixels.copy()

    def capture_window(self, window: MeetingWindowInfo) -> Optional[CapturedFrame]:
              if not window.is_observable:
                            return None
                        now = time.time()
        if self._synthetic_frame is not None:
                      frame = CapturedFrame(now, window.hwnd, window.rect, self._synthetic_frame.copy(), "synthetic")
                      self.ring_buffer.push(frame)
                      return frame
                  try:
                                import mss
                                with mss.mss() as sct:
                                                  monitor = {"left": window.rect.left, "top": window.rect.top, "width": window.rect.width, "height": window.rect.height}
                                                  raw = np.asarray(sct.grab(monitor), dtype=np.uint8)[:, :, :3]
                                                  frame = CapturedFrame(now, window.hwnd, window.rect, raw, "mss")
                                                  self.ring_buffer.push(frame)
                                                  return frame
                  except Exception:
            return None
