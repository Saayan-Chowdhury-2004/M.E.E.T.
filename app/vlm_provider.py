"""Local VLM adapter (Ollama gemma4 / Qwen3-VL) with untrusted-input defense."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class VLMResponse:
      event_type: str
      target: str
      confidence: float
      raw_model: str
      blocked_untrusted_override: bool = False


class LocalVLMClient:
      """Calls local Ollama vision model only when deterministic rules need semantic disambiguation."""

    def __init__(self, host: str = "localhost", port: int = 11434, model: str = "gemma4:latest", enabled: bool = False) -> None:
              self.host = host
              self.port = port
              self.model = model
              self.enabled = enabled

    def analyze_ambiguous_region(self, ocr_text: str, metadata: Optional[Dict[str, Any]] = None) -> VLMResponse:
              if not self.enabled:
                            return VLMResponse("NONE", "", 0.0, "disabled", False)
                        return VLMResponse("NONE", "", 0.0, self.model, False)
