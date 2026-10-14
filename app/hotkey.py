"""Win32 RegisterHotKey Kill Switch (`Ctrl+Alt+Shift+M`) eliminating LGPL `pynput` hooks."""
from __future__ import annotations

import ctypes
import sys
import threading
from typing import Callable, Optional

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
VK_M = 0x4D


class Win32KillSwitchHotkey:
      """Registers an OS-level hotkey via Win32 RegisterHotKey outside the AI loop."""

    def __init__(self, on_trigger: Callable[[], None], hotkey_id: int = 1001) -> None:
              self.on_trigger = on_trigger
              self.hotkey_id = hotkey_id
              self._thread: Optional[threading.Thread] = None
              self._stop_event = threading.Event()

    def start(self) -> bool:
              if sys.platform != "win32":
                            return False
                        self._stop_event.clear()
        self._thread = threading.Thread(target=self._win32_loop, daemon=True)
        self._thread.start()
        return True

    def trigger_simulated(self) -> None:
              self.on_trigger()

    def stop(self) -> None:
              self._stop_event.set()

    def _win32_loop(self) -> None:
              user32 = ctypes.windll.user32
        modifiers = MOD_CONTROL | MOD_ALT | MOD_SHIFT | MOD_NOREPEAT
        if not user32.RegisterHotKey(None, self.hotkey_id, modifiers, VK_M):
                      return
                  try:
                                class MSG(ctypes.Structure):
                                                  _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint), ("wParam", ctypes.c_size_t), ("lParam", ctypes.c_ssize_t), ("time", ctypes.c_uint), ("pt_x", ctypes.c_long), ("pt_y", ctypes.c_long)]
                                              msg = MSG()
            while not self._stop_event.is_set():
                              if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                                                    if msg.message == WM_HOTKEY and msg.wParam == self.hotkey_id:
                                                                              self.on_trigger()
                              else:
                    self._stop_event.wait(0.05)
finally:
            user32.UnregisterHotKey(None, self.hotkey_id)
