"""Windows Native UX: System Tray controller, interactive Toast notifications, and WebView2 HUD."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List

from app.rules_engine import ActionProposal


@dataclass
class ToastNotificationRecord:
      proposal_id: str
      title: str
      body: str
      actions: List[str]


class WindowsDesktopUX:
      """Manages native Windows Toast alerts (`ALLOW`/`BLOCK`) and WebView2 HUD window."""

    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
              self.dashboard_url = f"http://{host}:{port}"
              self.notifications: List[ToastNotificationRecord] = []

    def notify_action_suggestion(self, proposal: ActionProposal) -> ToastNotificationRecord:
              record = ToastNotificationRecord(
                            proposal_id=proposal.proposal_id,
                            title=f"M.E.E.T. Suggestion ({proposal.action_type})",
                            body=f"Target: {proposal.target} (Region: {proposal.source_region})",
                            actions=["ALLOW", "BLOCK"],
              )
              self.notifications.append(record)
              return record

    def launch_native_hud(self) -> bool:
              if sys.platform != "win32":
                            return False
                        try:
                                      import webview
                                      webview.create_window("M.E.E.T. — Local Third-Person Meeting Agent", self.dashboard_url, width=1080, height=720)
                                      webview.start()
                                      return True
except Exception:
            return False
