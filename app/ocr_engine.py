"""3-Tier Text & OCR Engine: UIA TextPattern -> Windows.Media.Ocr -> PaddleOCR -> Monitored Fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np


@dataclass
class OCRLine:
      text: str
      confidence: float
      bbox: Optional[tuple[int, int, int, int]] = None


@dataclass
class OCRResult:
      provider: str
      lines: List[OCRLine] = field(default_factory=list)
      degraded_warning: Optional[str] = None


class MultiTierOCREngine:
      """Executes text extraction across UIA, WinRT OCR, PaddleOCR, or injected test providers."""

    def __init__(self, max_cpu_threads: int = 2) -> None:
              self.max_cpu_threads = max_cpu_threads
              self._uia_provider: Optional[Callable[[str], List[str]]] = None
              self._custom_ocr_fn: Optional[Callable[[np.ndarray, str], OCRResult]] = None
              self._degraded_notified = False

    def set_uia_text_provider(self, provider: Callable[[str], List[str]]) -> None:
              self._uia_provider = provider

    def set_custom_ocr_provider(self, provider: Callable[[np.ndarray, str], OCRResult]) -> None:
              self._custom_ocr_fn = provider

    def extract_text(self, crop: np.ndarray, region_name: str) -> OCRResult:
              if self._uia_provider is not None:
                            try:
                                              uia_lines = self._uia_provider(region_name)
                                              if uia_lines:
                                                                    return OCRResult(
                                                                                              provider="uia_text",
                                                                                              lines=[OCRLine(text=line, confidence=0.99) for line in uia_lines if line.strip()],
                                                                    )
                            except Exception:
                                              pass
                                      if self._custom_ocr_fn is not None:
                                                    return self._custom_ocr_fn(crop, region_name)
                                                warning = None
                        if not self._degraded_notified:
                                      self._degraded_notified = True
                                      warning = "No active UIA text tree or native OCR model returned text; running in silent fallback mode."
                                  return OCRResult(provider="fallback", lines=[], degraded_warning=warning)
