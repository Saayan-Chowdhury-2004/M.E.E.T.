"""Token-authenticated Local Control Plane (`localhost:8765`)."""
from __future__ import annotations

import pathlib
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from app.agent import MeetAgent


class ControlPlaneDispatcher:
      """Core request router enforcing `X-MEET-Token` authentication."""

    def __init__(self, agent: MeetAgent) -> None:
              self.agent = agent

    def is_authorized(self, token: Optional[str]) -> bool:
              require_token = self.agent.default_cfg.get("api", {}).get("require_session_token", True)
              if not require_token:
                            return True
                        return bool(token and token == self.agent.session_token)

    def render_dashboard_html(self) -> str:
              dash_path = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dashboard" / "index.html"
        html = dash_path.read_text(encoding="utf-8")
        return html.replace("__MEET_SESSION_TOKEN__", self.agent.session_token)

    def handle_get(self, path: str, token: Optional[str]) -> Tuple[int, Dict[str, Any]]:
              if not self.is_authorized(token):
                            return 401, {"detail": "Invalid or missing X-MEET-Token header."}
                        parsed = urlparse(path)
        if parsed.path == "/status":
                      return 200, {
                                        "agent": "M.E.E.T.",
                                        "mode": self.agent.mode,
                                        "emergency_stop": self.agent.firewall.emergency_stop_active,
                                        "automation_enabled": self.agent.executor.automation_enabled,
                                        "ring_buffer_frames": len(self.agent.capture.ring_buffer),
                                        "pending_proposals": [
                                                              {"proposal_id": p.proposal_id, "action_type": p.action_type, "target": p.target, "domain": p.domain, "source_region": p.source_region}
                                                              for p in self.agent.pending_proposals.values()
                                        ],
                      }
                  if parsed.path == "/events":
                                qs = parse_qs(parsed.query)
                                limit = int(qs.get("limit", ["50"])[0])
                                return 200, {"events": self.agent.store.list_events(limit=limit)}
                            if parsed.path == "/rules":
                                          return 200, {"rules": self.agent.rules.list_rules()}
                                      return 404, {"detail": "Not found"}

    def handle_post(self, path: str, body: Dict[str, Any], token: Optional[str]) -> Tuple[int, Dict[str, Any]]:
              if not self.is_authorized(token):
                            return 401, {"detail": "Invalid or missing X-MEET-Token header."}
                        if path == "/mode":
                                      mode = body.get("mode", "")
                                      if mode not in ("observe", "suggest", "assist", "autonomous"):
                                                        return 400, {"detail": "Unsupported mode."}
                                                    self.agent.mode = mode
            return 200, {"mode": self.agent.mode}
        if path == "/emergency-stop":
                      self.agent.trigger_emergency_stop()
            return 200, {"emergency_stop": True, "mode": self.agent.mode}
        if path == "/emergency-reset":
                      self.agent.reset_emergency_stop()
            return 200, {"emergency_stop": False, "mode": self.agent.mode}
        if path == "/rules/compile":
                      try:
                                        rule = self.agent.rules.compile_natural_language_rule(str(body.get("instruction", "")))
                                        return 200, {"rule": rule}
except ValueError as exc:
                return 400, {"detail": str(exc)}
        if path == "/action/confirm":
                      verdict, outcome = self.agent.confirm_pending_proposal(str(body.get("proposal_id", "")), bool(body.get("allow", False)))
            return 200, {"allowed": verdict.allowed, "reason": verdict.reason, "failed_check": verdict.failed_check, "outcome": outcome.detail if outcome else None}
        return 404, {"detail": "Not found"}


def create_api(agent: MeetAgent) -> ControlPlaneDispatcher:
      return ControlPlaneDispatcher(agent)
