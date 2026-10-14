"""Main M.E.E.T. Orchestrator tying capture, ROI, 3-tier OCR, rules, firewall, and execution together."""
from __future__ import annotations

import pathlib
import secrets
from typing import Any, Dict, List, Optional

import yaml

from app.capture import WindowCaptureEngine
from app.dpi import enable_per_monitor_dpi_awareness
from app.event_engine import EventBus, MeetingEvent
from app.executor import ActionExecutor, ExecutionOutcome
from app.firewall import ActionFirewall, FirewallVerdict
from app.hotkey import Win32KillSwitchHotkey
from app.meeting_tracker import MeetingTracker, MeetingWindowInfo
from app.ocr_engine import MultiTierOCREngine
from app.roi_router import ROIRouter
from app.rules_engine import ActionProposal, RulesEngine
from app.storage import MetadataStore
from app.url_extractor import extract_urls_from_lines
from app.vlm_provider import LocalVLMClient
from app.windows_ux import WindowsDesktopUX


class MeetAgent:
      """Coordinates meeting observation, URL/event extraction, rule evaluation, and firewall-gated actions."""

    def __init__(self, config_dir: str | pathlib.Path = "config", db_path: str | pathlib.Path = ":memory:") -> None:
              self.config_dir = pathlib.Path(config_dir)
              self.default_cfg = self._load_yaml(self.config_dir / "default.yaml")
              self.policies_cfg = self._load_yaml(self.config_dir / "policies.yaml")
              self.rules_cfg = self._load_yaml(self.config_dir / "rules.yaml")

        enable_per_monitor_dpi_awareness()

        self.mode: str = self.default_cfg.get("agent", {}).get("default_mode", "observe")
        self.session_token: str = secrets.token_urlsafe(24)

        gating = self.default_cfg.get("meeting_gating", {})
        self.tracker = MeetingTracker(gating.get("process_names", []), gating.get("title_patterns", []))

        cap_cfg = self.default_cfg.get("capture", {})
        self.capture = WindowCaptureEngine(cap_cfg.get("backend", "auto"), float(cap_cfg.get("ring_buffer_seconds", 60.0)))

        reg_cfg = self.default_cfg.get("regions", {})
        self.roi_router = ROIRouter(
                      fallback_rois=reg_cfg.get("fallback_rois", {}),
                      pixel_change_threshold=int(reg_cfg.get("pixel_change_threshold", 12)),
                      dirty_pixel_ratio_trigger=float(reg_cfg.get("dirty_pixel_ratio_trigger", 0.008)),
                      video_motion_ceiling_ratio=float(reg_cfg.get("video_motion_ceiling_ratio", 0.45)),
        )

        ocr_cfg = self.default_cfg.get("ocr", {})
        self.ocr = MultiTierOCREngine(max_cpu_threads=int(ocr_cfg.get("max_cpu_threads", 2)))

        self.bus = EventBus()
        self.store = MetadataStore(db_path=db_path)
        self.rules = RulesEngine(store=self.store, initial_rules=self.rules_cfg.get("rules", []))

        vlm_cfg = self.default_cfg.get("vlm", {})
        self.vlm = LocalVLMClient(
                      host=vlm_cfg.get("host", "localhost"),
                      port=int(vlm_cfg.get("port", 11434)),
                      model=vlm_cfg.get("model", "gemma4:latest"),
                      enabled=bool(vlm_cfg.get("enabled", False)),
        )

        self.firewall = ActionFirewall(policy_cfg=self.policies_cfg)

        auto_cfg = self.default_cfg.get("automation", {})
        self.executor = ActionExecutor(
                      automation_enabled=bool(auto_cfg.get("enabled", False)),
                      prefer_shell_execute=bool(auto_cfg.get("prefer_shell_execute_for_urls", True)),
        )

        self.ux = WindowsDesktopUX()
        self.pending_proposals: Dict[str, ActionProposal] = {}
        self.hotkey = Win32KillSwitchHotkey(on_trigger=self.trigger_emergency_stop)

    @staticmethod
    def _load_yaml(path: pathlib.Path) -> Dict[str, Any]:
              with open(path, "r", encoding="utf-8") as f:
                            return yaml.safe_load(f) or {}

          def trigger_emergency_stop(self) -> None:
                    self.firewall.trigger_emergency_stop()
                    self.mode = "observe"
                    self.pending_proposals.clear()

    def reset_emergency_stop(self) -> None:
              self.firewall.reset_emergency_stop()

    async def step_once(self) -> Dict[str, Any]:
              window: Optional[MeetingWindowInfo] = self.tracker.find_active_meeting()
              if window is None:
                            return {"status": "standby", "events_emitted": 0, "proposals": []}

              frame = self.capture.capture_window(window)
              if frame is None:
                            return {"status": "no_frame", "events_emitted": 0, "proposals": []}

              roi_results = self.roi_router.evaluate_frame(frame, window)
              emitted_events: List[MeetingEvent] = []
              created_proposals: List[ActionProposal] = []
              outcomes: List[ExecutionOutcome] = []

        for roi in roi_results:
                      if not roi.is_changed:
                                        continue

                      ocr_res = self.ocr.extract_text(roi.crop, roi.region_name)
                      if ocr_res.degraded_warning:
                                        warn_evt = MeetingEvent.create("ENGINE_WARNING", roi.region_name, {"warning": ocr_res.degraded_warning}, 1.0, window.hwnd)
                                        self.store.record_event(warn_evt)
                                        await self.bus.publish(warn_evt)

                      raw_lines = [line.text for line in ocr_res.lines]
                      for item in extract_urls_from_lines(raw_lines):
                                        evt = MeetingEvent.create(
                                                              event_type="NEW_URL",
                                                              source_region=roi.region_name,
                                                              payload={"url": item.url, "domain": item.domain, "was_stitched": item.was_stitched, "ocr_provider": ocr_res.provider},
                                                              confidence=item.confidence,
                                                              window_hwnd=window.hwnd,
                                        )
                                        self.store.record_event(evt)
                                        await self.bus.publish(evt)
                                        emitted_events.append(evt)

                          for prop in self.rules.evaluate(evt):
                                                created_proposals.append(prop)
                                                if self.mode == "suggest":
                                                                          self.pending_proposals[prop.proposal_id] = prop
                                                                          self.ux.notify_action_suggestion(prop)
elif self.mode in ("assist", "autonomous"):
                        verdict = self.firewall.evaluate(prop, self.mode, window.process_name)
                        if verdict.allowed:
                                                      outcomes.append(self.executor.execute(prop))

        return {
                      "status": "active",
                      "meeting_title": window.title,
                      "events_emitted": len(emitted_events),
                      "proposals": [p.proposal_id for p in created_proposals],
                      "outcomes": [o.detail for o in outcomes],
        }

    def confirm_pending_proposal(self, proposal_id: str, allow: bool, active_process_name: str = "Zoom.exe") -> tuple[FirewallVerdict, Optional[ExecutionOutcome]]:
              prop = self.pending_proposals.pop(proposal_id, None)
        if prop is None:
                      return FirewallVerdict(False, "Proposal not found.", "not_found"), None
        if not allow:
                      return FirewallVerdict(False, "Blocked by user.", "user_blocked"), None
        verdict = self.firewall.evaluate(prop, self.mode, active_process_name, user_confirmed=True)
        if not verdict.allowed:
                      return verdict, None
        return verdict, self.executor.execute(prop)
