"""Dynamic ROI routing, pixel-ratio change detection, and video-tile motion suppression."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from app.capture import CapturedFrame
from app.dpi import Rect
from app.meeting_tracker import MeetingWindowInfo


@dataclass
class ROIChangeResult:
      region_name: str
      rect: Rect
      crop: np.ndarray
      dirty_ratio: float
      is_changed: bool
      suppressed_as_video_motion: bool


class ROIRouter:
      """Routes meeting window sub-regions and detects meaningful text changes while suppressing video noise."""

    def __init__(
              self,
              fallback_rois: Dict[str, Dict[str, float]],
              pixel_change_threshold: int = 12,
              dirty_pixel_ratio_trigger: float = 0.008,
              video_motion_ceiling_ratio: float = 0.45,
    ) -> None:
              self.fallback_rois = fallback_rois
              self.pixel_change_threshold = pixel_change_threshold
              self.dirty_pixel_ratio_trigger = dirty_pixel_ratio_trigger
              self.video_motion_ceiling_ratio = video_motion_ceiling_ratio
              self._last_crops: Dict[str, np.ndarray] = {}

    def resolve_rois(self, window: MeetingWindowInfo) -> Dict[str, Rect]:
              rois: Dict[str, Rect] = {}
              for name, cfg in self.fallback_rois.items():
                            if name == "chat_sidebar" and window.chat_pane_rect is not None:
                                              rois[name] = window.chat_pane_rect
else:
                rois[name] = window.rect.sub_rect(
                                      float(cfg.get("x_ratio", 0.0)),
                                      float(cfg.get("y_ratio", 0.0)),
                                      float(cfg.get("w_ratio", 1.0)),
                                      float(cfg.get("h_ratio", 1.0)),
                )
          return rois

    def evaluate_frame(self, frame: CapturedFrame, window: MeetingWindowInfo) -> List[ROIChangeResult]:
              rois = self.resolve_rois(window)
              results: List[ROIChangeResult] = []
              fh, fw = frame.pixels.shape[:2]

        for name, rect in rois.items():
                      x0 = max(0, min(fw - 1, rect.left - window.rect.left))
                      y0 = max(0, min(fh - 1, rect.top - window.rect.top))
                      x1 = max(x0 + 1, min(fw, x0 + rect.width))
                      y1 = max(y0 + 1, min(fh, y0 + rect.height))
                      crop = frame.pixels[y0:y1, x0:x1]

            prev = self._last_crops.get(name)
            if prev is None or prev.shape != crop.shape:
                              self._last_crops[name] = crop.copy()
                              results.append(ROIChangeResult(name, rect, crop, 1.0, True, False))
                              continue

            diff = np.abs(crop.astype(np.int16) - prev.astype(np.int16))
            changed_mask = np.max(diff, axis=2) > self.pixel_change_threshold
            dirty_ratio = float(np.mean(changed_mask))
            is_video_motion = name != "chat_sidebar" and dirty_ratio > self.video_motion_ceiling_ratio
            is_changed = (dirty_ratio >= self.dirty_pixel_ratio_trigger) and not is_video_motion
            if is_changed:
                              self._last_crops[name] = crop.copy()
                          results.append(ROIChangeResult(name, rect, crop, dirty_ratio, is_changed, is_video_motion))
        return results
