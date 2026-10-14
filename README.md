# M.E.E.T. — Local Third-Person Meeting Agent for Windows

**M.E.E.T.** (*Meeting Event Evaluation & Triage*) is a local-first, open-source **Windows computer-use observer agent**. It watches your active meeting window from outside the meeting application (Google Meet, Microsoft Teams, Zoom, Webex), detects important events as they happen, and performs **pre-authorized, low-risk actions** — such as opening allowlisted links shared in the meeting chat — without cloud AI, subscriptions, or invasive bots joining the call.

## Windows-Native Architecture

- **HWND-Isolated Capture (`app/capture.py`)**: Uses Windows Graphics Capture (`WGC`) with `mss` fallback and a 60-second RAM ring buffer so overlapping desktop windows never leak into capture.
- **Per-Monitor DPI V2 Normalization (`app/dpi.py`)**: Enforces `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2` across multi-monitor setups.
- **Dynamic UIA ROI Router & Motion Suppression (`app/roi_router.py`)**: Anchors ROIs to Windows UI Automation control bounds and suppresses video-tile motion (`>0.45` dirty ratio) to prevent OCR CPU thrashing.
- **3-Tier Text & OCR Engine (`app/ocr_engine.py`)**: Reads chat text directly via Windows UI Automation (`UIA`) TextPattern (0 ms) -> `Windows.Media.Ocr` (WinRT) -> `PaddleOCR`, with explicit engine health telemetry.
- **Multi-Line URL Stitcher (`app/url_extractor.py`)**: Reconstructs long URLs soft-wrapped across narrow chat sidebars before deterministic regex extraction.
- **10-Check Action Firewall (`app/firewall.py`)**: Enforces emergency stop, action schema, risk class, mode capability, app allowlist, screen-share visual spoof guard, domain allowlist/blocklist, confidence gate, deduplication, and TOCTOU revalidation.
- **Cursor-Free OS Executor (`app/executor.py`)**: Opens allowlisted URLs via Win32 `ShellExecuteW` without moving the user's physical mouse cursor or stealing focus.
- **Win32 Hardware Kill Switch (`app/hotkey.py`)**: Registers `Ctrl+Alt+Shift+M` via Win32 `RegisterHotKey` (zero LGPL `pynput` dependency).
- **Authenticated Control Plane & Native HUD (`app/api.py`, `app/windows_ux.py`)**: Protects `127.0.0.1:8765` with per-session `X-MEET-Token` authentication, interactive Windows Toast notifications, and a WebView2 HUD.

## Quick Start (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
.\.venv\Scripts\python -m pytest tests -v
.\.venv\Scripts\python -m app.benchmark
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

