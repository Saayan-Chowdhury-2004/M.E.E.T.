"""10-Check Action Firewall (spec §16) with TOCTOU Revalidation & Screen-Share Spoof Guard."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.rules_engine import ActionProposal


@dataclass
class FirewallVerdict:
      allowed: bool
      reason: str
      failed_check: Optional[str] = None
      checks_passed: List[str] = field(default_factory=list)


class ActionFirewall:
      """Enforces the 10 mandatory safety checks before any OS action can execute."""

    def __init__(self, policy_cfg: Dict[str, Any]) -> None:
              self.policy_cfg = policy_cfg
              self.emergency_stop_active: bool = False
              self._executed_hashes: Dict[str, float] = {}

    def trigger_emergency_stop(self) -> None:
              self.emergency_stop_active = True

    def reset_emergency_stop(self) -> None:
              self.emergency_stop_active = False

    def evaluate(
              self,
              proposal: ActionProposal,
              current_mode: str,
              active_process_name: str,
              live_content_validator: Optional[Callable[[ActionProposal], bool]] = None,
              user_confirmed: bool = False,
              now: Optional[float] = None,
    ) -> FirewallVerdict:
              current_time = now if now is not None else time.time()
              passed: List[str] = []

        if self.emergency_stop_active:
                      return FirewallVerdict(False, "Emergency stop is active.", "check_1_emergency_stop", passed)
                  passed.append("check_1_emergency_stop")

        allowed_actions = self.policy_cfg.get("allowed_actions", {})
        if proposal.action_type not in allowed_actions:
                      return FirewallVerdict(False, "Action not in permitted schema.", "check_2_action_schema", passed)
                  passed.append("check_2_action_schema")

        action_spec = allowed_actions[proposal.action_type]
        risk_level = action_spec.get("risk_level", "high")
        if risk_level == "high":
                      return FirewallVerdict(False, "High-risk actions are prohibited.", "check_3_risk_class", passed)
                  passed.append("check_3_risk_class")

        mode_caps = self.policy_cfg.get("mode_capabilities", {}).get(current_mode, {})
        if not user_confirmed:
                      if not mode_caps.get("allow_execution", False) or risk_level not in mode_caps.get("allowed_risk_levels", []):
                                        return FirewallVerdict(False, "Mode does not permit autonomous execution.", "check_4_mode_capability", passed)
                                passed.append("check_4_mode_capability")

        app_allowlist = {a.lower() for a in self.policy_cfg.get("app_allowlist", [])}
        if active_process_name.lower() not in app_allowlist:
                      return FirewallVerdict(False, "Process not in meeting app allowlist.", "check_5_app_allowlist", passed)
        passed.append("check_5_app_allowlist")

        sec_cfg = self.policy_cfg.get("security", {})
        if sec_cfg.get("block_urls_from_screen_share_region", True) and proposal.action_type == "open_url" and proposal.source_region == "screen_share_canvas":
                      return FirewallVerdict(False, "Blocked URL from untrusted screen-share canvas.", "check_6_screen_share_spoof_guard", passed)
        passed.append("check_6_screen_share_spoof_guard")

        if proposal.action_type == "open_url":
                      domain = proposal.domain.lower()
            blocklist = {d.lower() for d in self.policy_cfg.get("domain_blocklist", [])}
            allowlist = {d.lower() for d in self.policy_cfg.get("domain_allowlist", [])}
            if any(b in domain for b in blocklist):
                              return FirewallVerdict(False, "Domain is blocked.", "check_7_domain_policy", passed)
                          if not any(a in domain for a in allowlist):
                                            return FirewallVerdict(False, "Domain is not in allowlist.", "check_7_domain_policy", passed)
                                    passed.append("check_7_domain_policy")

        min_conf = float(sec_cfg.get("min_confidence", 0.80))
        if not user_confirmed and proposal.confidence < min_conf:
                      return FirewallVerdict(False, "Confidence below threshold.", "check_8_confidence_gate", passed)
        passed.append("check_8_confidence_gate")

        dedup_window = float(sec_cfg.get("deduplicate_window_seconds", 120.0))
        dedup_key = f"{proposal.action_type}:{proposal.target}"
        last_exec = self._executed_hashes.get(dedup_key)
        if last_exec is not None and (current_time - last_exec) < dedup_window:
                      return FirewallVerdict(False, "Duplicate action suppressed.", "check_9_deduplication", passed)
        passed.append("check_9_deduplication")

        max_age_ms = float(sec_cfg.get("max_target_age_ms", 2500.0))
        if not user_confirmed and ((current_time - proposal.created_at) * 1000.0) > max_age_ms:
                      return FirewallVerdict(False, "Target proposal expired TOCTOU window.", "check_10_toctou_revalidation", passed)
        if live_content_validator is not None and not live_content_validator(proposal):
                      return FirewallVerdict(False, "Live target revalidation failed.", "check_10_toctou_revalidation", passed)
        passed.append("check_10_toctou_revalidation")

        self._executed_hashes[dedup_key] = current_time
        return FirewallVerdict(True, "All 10 Action Firewall checks passed.", None, passed)
