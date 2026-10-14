"""Meeting window detector using Win32 HWND enumeration and UI Automation tab title scanning."""
from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.dpi import Rect


@dataclass
class MeetingWindowInfo:
      hwnd: int
      title: str
      process_name: str
      rect: Rect
      is_minimized: bool = False
      is_visible: bool = True
      chat_pane_rect: Optional[Rect] = None
      metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def is_observable(self) -> bool:
              return (
                            self.is_visible
                            and not self.is_minimized
                            and self.rect.width >= 160
                            and self.rect.height >= 120
              )


class MeetingTracker:
      """Tracks active meeting windows (Zoom, Teams, Meet, Webex) and resolves their bounding box."""

    def __init__(self, process_names: List[str], title_patterns: List[str]) -> None:
              self.process_names = [p.lower() for p in process_names]
              self.title_patterns = [t.lower() for t in title_patterns]
              self._mock_window: Optional[MeetingWindowInfo] = None

    def set_mock_window(self, window: Optional[MeetingWindowInfo]) -> None:
              self._mock_window = window

    def find_active_meeting(self) -> Optional[MeetingWindowInfo]:
              if self._mock_window is not None:
                            return self._mock_window if self._mock_window.is_observable else None
                        if sys.platform != "win32":
                                      return None
                                  return self._enum_win32_meeting_windows()

    def _matches_title(self, title: str) -> bool:
              low = title.lower()
        return any(pat in low for pat in self.title_patterns)

    def _enum_win32_meeting_windows(self) -> Optional[MeetingWindowInfo]:
              user32 = ctypes.windll.user32
        found: List[MeetingWindowInfo] = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        class WINRECT(ctypes.Structure):
                      _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        def callback(hwnd: int, _lparam: int) -> bool:
                      if not user32.IsWindowVisible(hwnd):
                                        return True
                                    length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                              return True
                          buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if not self._matches_title(title):
                              return True
                          is_iconic = bool(user32.IsIconic(hwnd))
            wrect = WINRECT()
            user32.GetWindowRect(hwnd, ctypes.byref(wrect))
            rect = Rect(wrect.left, wrect.top, max(0, wrect.right - wrect.left), max(0, wrect.bottom - wrect.top))
            info = MeetingWindowInfo(hwnd=int(hwnd), title=title, process_name="Zoom.exe", rect=rect, is_minimized=is_iconic, is_visible=True)
            if info.is_observable:
                              found.append(info)
                              return False
                          return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found[0] if found else None
