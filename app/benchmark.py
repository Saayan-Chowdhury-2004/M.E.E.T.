"""Spec §35 Pipeline Latency and Throughput Benchmark Report."""
from __future__ import annotations

import asyncio
import time
import numpy as np

from app.agent import MeetAgent
from app.dpi import Rect
from app.meeting_tracker import MeetingWindowInfo
from app.ocr_engine import OCRLine, OCRResult


async def run_benchmark(iterations: int = 50) -> dict:
      agent = MeetAgent(config_dir="config")
      window = MeetingWindowInfo(hwnd=9901, title="Google Meet - Product Sync", process_name="chrome.exe", rect=Rect(0, 0, 1280, 720))
      agent.tracker.set_mock_window(window)

    base_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    sample_prefix = "https" + "://docs." + "google" + ".com/document/d/1Bench-"
    agent.ocr.set_custom_ocr_provider(
              lambda _crop, _region: OCRResult(
                            provider="winrt_ocr_sim",
                            lines=[
                                              OCRLine(f"Shared doc: {sample_prefix}", 0.96),
                                              OCRLine("MarkTestDoc_2026/edit", 0.96),
                            ],
              )
    )

    latencies_ms = []
    for i in range(iterations):
              frame = base_frame.copy()
              frame[100:220, 950:1200] = (i * 17) % 255
              agent.capture.set_synthetic_frame(frame)
              t0 = time.perf_counter()
              await agent.step_once()
              latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    report = {
              "iterations": iterations,
              "avg_step_latency_ms": round(float(np.mean(latencies_ms)), 3),
              "p95_step_latency_ms": round(float(np.percentile(latencies_ms, 95)), 3),
              "events_recorded": len(agent.store.list_events(limit=200)),
    }
    print("=== M.E.E.T. Pipeline Benchmark ===")
    for k, v in report.items():
              print(f"  {k}: {v}")
          return report


if __name__ == "__main__":
      asyncio.run(run_benchmark())
