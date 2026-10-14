"""Comprehensive test suite for M.E.E.T. (compatible with both pytest and unittest)."""
from __future__ import annotations

import asyncio
import time
import unittest
import numpy as np

from app.agent import MeetAgent
from app.api import create_api
from app.dpi import Rect, normalize_rect_for_dpi
from app.meeting_tracker import MeetingWindowInfo
from app.rules_engine import ActionProposal
from app.url_extractor import extract_urls_from_lines, stitch_wrapped_url_lines

HTTPS = "https" + "://"
DOCS_HOST = "docs." + "google" + ".com"
GH_HOST = "github" + ".com"
FIGMA_HOST = "figma" + ".com"


class TestMeetPipeline(unittest.TestCase):
      def test_dpi_coordinate_normalization(self) -> None:
                logical = Rect(left=100, top=200, width=800, height=600)
                physical = normalize_rect_for_dpi(logical, scale_factor=1.5)
                self.assertEqual(physical.left, 150)
                self.assertEqual(physical.top, 300)
                self.assertEqual(physical.width, 1200)
                self.assertEqual(physical.height, 900)

      def test_multiline_wrapped_url_stitching(self) -> None:
                chat_lines = [
                              "Alice: Please review the architecture doc:",
                              f"{HTTPS}{DOCS_HOST}/document/d/1AbCdEfGhIjKlMnOpQrSt-",
                              "UvWxYz_0123456789/edit?usp=sharing",
                              "Thanks!",
                ]
                stitched = stitch_wrapped_url_lines(chat_lines)
                self.assertEqual(len(stitched), 3)
                extracted = extract_urls_from_lines(chat_lines)
                self.assertEqual(len(extracted), 1)
                self.assertEqual(
                    extracted[0].url,
                    f"{HTTPS}{DOCS_HOST}/document/d/1AbCdEfGhIjKlMnOpQrSt-UvWxYz_0123456789/edit?usp=sharing",
                )
                self.assertEqual(extracted[0].domain, DOCS_HOST)
                self.assertTrue(extracted[0].was_stitched)

      def test_video_motion_suppression_prevents_ocr_thrashing(self) -> None:
                agent = MeetAgent(config_dir="config")
                win = MeetingWindowInfo(hwnd=101, title="Zoom Meeting", process_name="Zoom.exe", rect=Rect(0, 0, 1280, 720))
                f1 = np.zeros((720, 1280, 3), dtype=np.uint8)
                agent.capture.set_synthetic_frame(f1)
                frame1 = agent.capture.capture_window(win)
                self.assertIsNotNone(frame1)
                agent.roi_router.evaluate_frame(frame1, win)

          f2 = f1.copy()
        f2[540:684, 192:896] = 255
        agent.capture.set_synthetic_frame(f2)
        frame2 = agent.capture.capture_window(win)
        self.assertIsNotNone(frame2)
        results = {r.region_name: r for r in agent.roi_router.evaluate_frame(frame2, win)}
        self.assertTrue(results["meeting_Banner"].suppressed_as_video_motion)
        self.assertFalse(results["meeting_Banner"].is_changed)
        self.assertFalse(results["chat_sidebar"].is_changed)

    def test_action_firewall_10_checks_and_screen_share_spoof_guard(self) -> None:
              agent = MeetAgent(config_dir="config")
              agent.mode = "assist"
              now = time.time()

        valid_prop = ActionProposal(
                      proposal_id="p1",
                      rule_id="r1",
                      action_type="open_url",
                      target=f"{HTTPS}{GH_HOST}/example/repo",
                      domain=GH_HOST,
                      source_region="chat_sidebar",
                      confidence=0.95,
                      content_hash="h1",
                      window_hwnd=101,
                      created_at=now,
                      metadata={},
        )
        v1 = agent.firewall.evaluate(valid_prop, current_mode="assist", active_process_name="Zoom.exe", now=now)
        self.assertTrue(v1.allowed)
        self.assertEqual(len(v1.checks_passed), 10)

        v_dup = agent.firewall.evaluate(valid_prop, current_mode="assist", active_process_name="Zoom.exe", now=now + 5)
        self.assertFalse(v_dup.allowed)
        self.assertEqual(v_dup.failed_check, "check_9_deduplication")

        spoof_prop = ActionProposal(
                      proposal_id="p2",
                      rule_id="r1",
                      action_type="open_url",
                      target=f"{HTTPS}{GH_HOST}/malicious/spoof",
                      domain=GH_HOST,
                      source_region="screen_share_canvas",
                      confidence=0.98,
                      content_hash="h2",
                      window_hwnd=101,
                      created_at=now,
                      metadata={},
        )
        v_spoof = agent.firewall.evaluate(spoof_prop, current_mode="assist", active_process_name="Zoom.exe", now=now)
        self.assertFalse(v_spoof.allowed)
        self.assertEqual(v_spoof.failed_check, "check_6_screen_share_spoof_guard")

        stale_prop = ActionProposal(
                      proposal_id="p3",
                      rule_id="r1",
                      action_type="open_url",
                      target=f"{HTTPS}{FIGMA_HOST}/file/123",
                      domain=FIGMA_HOST,
                      source_region="chat_sidebar",
                      confidence=0.95,
                      content_hash="h3",
                      window_hwnd=101,
                      created_at=now - 10.0,
                      metadata={},
        )
        v_stale = agent.firewall.evaluate(stale_prop, current_mode="assist", active_process_name="Zoom.exe", now=now)
        self.assertFalse(v_stale.allowed)
        self.assertEqual(v_stale.failed_check, "check_10_toctou_revalidation")

    def test_end_to_end_uia_pipeline_and_api_token_security(self) -> None:
              agent = MeetAgent(config_dir="config")
              agent.mode = "suggest"
              win = MeetingWindowInfo(hwnd=555, title="Microsoft Teams - Architecture Review", process_name="ms-teams.exe", rect=Rect(0, 0, 1280, 720))
              agent.tracker.set_mock_window(win)
              agent.capture.set_synthetic_frame(np.ones((720, 1280, 3), dtype=np.uint8) * 40)

        agent.ocr.set_uia_text_provider(
                      lambda region: [f"Bob: Check the PR {HTTPS}{GH_HOST}/microsoft/", "terminal/pull/1420"]
                      if region == "chat_sidebar"
                      else []
        )

        res = asyncio.run(agent.step_once())
        self.assertEqual(res["status"], "active")
        self.assertEqual(res["events_emitted"], 1)
        self.assertEqual(len(res["proposals"]), 1)

        dispatcher = create_api(agent)
        code_unauth, _ = dispatcher.handle_get("/status", token=None)
        self.assertEqual(code_unauth, 401)

        code_ok, payload = dispatcher.handle_get("/status", token=agent.session_token)
        self.assertEqual(code_ok, 200)
        pending = payload["pending_proposals"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["target"], f"{HTTPS}{GH_HOST}/microsoft/terminal/pull/1420")

        code_conf, conf_payload = dispatcher.handle_post(
                      "/action/confirm",
                      body={"proposal_id": pending[0]["proposal_id"], "allow": True},
                      token=agent.session_token,
        )
        self.assertEqual(code_conf, 200)
        self.assertTrue(conf_payload["allowed"])


if __name__ == "__main__":
      unittest.main()
