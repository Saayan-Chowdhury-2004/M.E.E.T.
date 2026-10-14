"""Multi-line soft-wrap URL stitcher and deterministic URL regex extractor."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

SCHEME_HTTP = "http" + "://"
SCHEME_HTTPS = "https" + "://"
URL_REGEX = re.compile(r"(https?://" + r"[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+)", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedURL:
      url: str
      domain: str
      was_stitched: bool
      confidence: float


def stitch_wrapped_url_lines(lines: List[str]) -> List[str]:
      """Reconstructs URLs that wrapped across narrow meeting chat lines."""
      if not lines:
                return []
            stitched: List[str] = []
    i = 0
    while i < len(lines):
              current = lines[i].strip()
              while (
                            i + 1 < len(lines)
                            and (SCHEME_HTTP in current.lower() or SCHEME_HTTPS in current.lower())
                            and _looks_like_url_continuation(current, lines[i + 1].strip())
              ):
                            current = current + lines[i + 1].strip()
                            i += 1
                        stitched.append(current)
        i += 1
    return stitched


def _looks_like_url_continuation(current_line: str, next_line: str) -> bool:
      if not next_line or " " in next_line:
                return False
            if next_line.lower().startswith((SCHEME_HTTP, SCHEME_HTTPS)):
                      return False
                  tokens = current_line.split()
    if not tokens or not tokens[-1].lower().startswith((SCHEME_HTTP, SCHEME_HTTPS)):
              return False
    return bool(re.match(r"^[A-Za-z0-9/_?=&%#\-.~+=]+$", next_line))


def sanitize_ocr_url(raw_url: str) -> str:
      cleaned = raw_url.strip().rstrip(".,;:!?)\"'>")
    return cleaned


def extract_urls_from_lines(lines: List[str], base_confidence: float = 0.92) -> List[ExtractedURL]:
      raw_joined = "\n".join(lines)
    stitched_lines = stitch_wrapped_url_lines(lines)
    results: List[ExtractedURL] = []
    seen = set()
    for line in stitched_lines:
              for match in URL_REGEX.finditer(line):
                            candidate = sanitize_ocr_url(match.group(1))
                            if "…" in candidate or candidate.endswith("..."):
                                              continue
                                          parsed = urlparse(candidate)
            domain = (parsed.hostname or "").lower()
            if not domain or "." not in domain:
                              continue
                          if candidate not in seen:
                                            seen.add(candidate)
                                            results.append(ExtractedURL(candidate, domain, candidate not in raw_joined, base_confidence))
                                return results
