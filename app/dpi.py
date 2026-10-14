"""Per-Monitor DPI V2 awareness and coordinate normalization for Windows."""
from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
      left: int
      top: int
      width: int
      height: int

    @property
    def right(self) -> int:
              return self.left + self.width

    @property
    def bottom(self) -> int:
              return self.top + self.height

    def sub_rect(self, x_ratio: float, y_ratio: float, w_ratio: float, h_ratio: float) -> "Rect":
              return Rect(
                            left=int(self.left + self.width * x_ratio),
                            top=int(self.top + self.height * y_ratio),
                            width=max(1, int(self.width * w_ratio)),
                            height=max(1, int(self.height * h_ratio)),
              )


def enable_per_monitor_dpi_awareness() -> bool:
      """Enables Per-Monitor V2 DPI awareness on Windows so physical and logical coordinates align."""
      if sys.platform != "win32":
                return False
            try:
                      user32 = ctypes.windll.user32
                      res = user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
                      if res:
                                    return True
                                ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return True
except Exception:
        return False


def normalize_rect_for_dpi(rect: Rect, scale_factor: float = 1.0) -> Rect:
      """Converts logical window coordinates into physical framebuffer coordinates given a monitor scale."""
    if scale_factor <= 0:
              raise ValueError("scale_factor must be positive")
    if abs(scale_factor - 1.0) < 1e-4:
              return rect
    return Rect(
              left=int(round(rect.left * scale_factor)),
              top=int(round(rect.top * scale_factor)),
              width=max(1, int(round(rect.width * scale_factor))),
              height=max(1, int(round(rect.height * scale_factor))),
    )
