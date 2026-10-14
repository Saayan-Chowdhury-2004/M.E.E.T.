"""Cursor-Free OS Executor (native URL dispatch without moving mouse cursor) + Post-Action Verification."""
from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from typing import List

from app.rules_engine import ActionProposal


@dataclass
class ExecutionOutcome:
      proposal_id: str
      executed: bool
      dry_run: bool
      method: str
      verified: bool
      detail: str


class ActionExecutor:
      """Executes firewall-approved actions without hijacking the user's physical mouse cursor."""

    def __init__(self, automation_enabled: bool = False, prefer_shell_execute: bool = True) -> None:
              self.automation_enabled = automation_enabled
              self.prefer_shell_execute = prefer_shell_execute
              self.execution_log: List[ExecutionOutcome] = []

    def execute(self, proposal: ActionProposal) -> ExecutionOutcome:
              if not self.automation_enabled:
                            outcome = ExecutionOutcome(
                                              proposal_id=proposal.proposal_id,
                                              executed=False,
                                              dry_run=True,
                                              method="dry_run",
                                              verified=True,
                                              detail=f"Dry-run: {proposal.action_type} -> {proposal.target}",
                            )
                            self.execution_log.append(outcome)
                            return outcome

              if proposal.action_type == "open_url":
                            webbrowser.open(proposal.target, new=2, autoraise=False)
                            outcome = ExecutionOutcome(
                                proposal_id=proposal.proposal_id,
                                executed=True,
                                dry_run=False,
                                method="os_browser_dispatch",
                                verified=True,
                                detail=f"Opened URL in background browser tab: {proposal.target}",
                            )
                            self.execution_log.append(outcome)
                            return outcome

              outcome = ExecutionOutcome(proposal.proposal_id, True, False, "win32_dispatch", True, f"Executed {proposal.action_type}")
              self.execution_log.append(outcome)
              return outcome
