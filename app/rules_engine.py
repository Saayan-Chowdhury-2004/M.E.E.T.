"""Deterministic Rules Engine and Natural-Language-to-Validated-Rule Compiler."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.event_engine import MeetingEvent
from app.storage import MetadataStore


@dataclass
class ActionProposal:
      proposal_id: str
      rule_id: str
      action_type: str
      target: str
      domain: str
      source_region: str
      confidence: float
      content_hash: str
      window_hwnd: int
      created_at: float
      metadata: Dict[str, Any]


class RulesEngine:
      """Evaluates structured rules deterministically before any VLM fallback is needed."""

    def __init__(self, store: MetadataStore, initial_rules: Optional[List[Dict[str, Any]]] = None) -> None:
              self.store = store
              if initial_rules:
                            existing_ids = {r["id"] for r in self.store.list_rules()}
                            for rule in initial_rules:
                                              if rule["id"] not in existing_ids:
                                                                    self.store.upsert_rule(rule)

                                  def list_rules(self) -> List[Dict[str, Any]]:
                                            return self.store.list_rules()

                    def evaluate(self, event: MeetingEvent) -> List[ActionProposal]:
                              proposals: List[ActionProposal] = []
                              for rule in self.store.list_rules():
                                            if not rule.get("enabled", True) or rule["event_type"] != event.event_type:
                                                              continue
                                                          region_filter = rule.get("source_region", "*")
                                            if region_filter not in ("*", event.source_region):
                                                              continue
                                                          action_type = rule.get("action_type", "none")
                                            if action_type == "none":
                                                              continue
                                                          proposals.append(
                                                ActionProposal(
                                                    proposal_id=f"prop_{uuid.uuid4().hex[:10]}",
                                                    rule_id=rule["id"],
                                                    action_type=action_type,
                                                    target=str(event.payload.get("url") or event.payload.get("target") or ""),
                                                    domain=str(event.payload.get("domain") or ""),
                                                    source_region=event.source_region,
                                                    confidence=event.confidence,
                                                    content_hash=event.content_hash,
                                                    window_hwnd=event.window_hwnd,
                                                    created_at=event.timestamp,
                                                    metadata={"rule_name": rule["name"]},
                                                )
                                            )
                                        return proposals

    def compile_natural_language_rule(self, instruction: str) -> Dict[str, Any]:
              text = instruction.strip()
        low = text.lower()
        if "link" in low or "url" in low:
                      action_type = "open_url" if ("open" in low or "launch" in low) else "copy_to_clipboard"
            region = "chat_sidebar" if "chat" in low else "*"
            rule = {
                              "id": f"rule_custom_{uuid.uuid4().hex[:8]}",
                              "name": text[:80],
                              "enabled": True,
                              "event_type": "NEW_URL",
                              "source_region": region,
                              "action_type": action_type,
                              "require_allowlisted_domain": True,
                              "description": f"Compiled from instruction: {text}",
            }
            self.store.upsert_rule(rule)
            return rule
        raise ValueError("Instruction did not match any supported safe deterministic rule pattern.")
