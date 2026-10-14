"""SQLite persistence for structured event metadata and custom rules (no media/frames stored)."""
from __future__ import annotations

import json
import pathlib
import sqlite3
from typing import Any, Dict, List

from app.event_engine import MeetingEvent


class MetadataStore:
      """Persists event metadata and rule states in SQLite."""

    def __init__(self, db_path: str | pathlib.Path = ":memory:") -> None:
              self.db_path = str(db_path)
              if self.db_path != ":memory:":
                            pathlib.Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
                        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
              cur = self._conn.cursor()
        cur.execute(
                      """
                                  CREATE TABLE IF NOT EXISTS events (
                                                  event_id TEXT PRIMARY KEY,
                                                                  timestamp REAL NOT NULL,
                                                                                  event_type TEXT NOT NULL,
                                                                                                  source_region TEXT NOT NULL,
                                                                                                                  confidence REAL NOT NULL,
                                                                                                                                  content_hash TEXT NOT NULL,
                                                                                                                                                  payload_json TEXT NOT NULL
                                                                                                                                                              )
                                                                                                                                                                          """
        )
        cur.execute(
                      """
                                  CREATE TABLE IF NOT EXISTS rules (
                                                  rule_id TEXT PRIMARY KEY,
                                                                  name TEXT NOT NULL,
                                                                                  enabled INTEGER NOT NULL,
                                                                                                  event_type TEXT NOT NULL,
                                                                                                                  source_region TEXT NOT NULL,
                                                                                                                                  action_type TEXT NOT NULL,
                                                                                                                                                  require_allowlisted_domain INTEGER NOT NULL,
                                                                                                                                                                  description TEXT NOT NULL
                                                                                                                                                                              )
                                                                                                                                                                                          """
        )
        self._conn.commit()

    def record_event(self, event: MeetingEvent) -> None:
              cur = self._conn.cursor()
        cur.execute(
                      "INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (
                                        event.event_id,
                                        event.timestamp,
                                        event.event_type,
                                        event.source_region,
                                        event.confidence,
                                        event.content_hash,
                                        json.dumps(event.payload),
                      ),
        )
        self._conn.commit()

    def list_events(self, limit: int = 50) -> List[Dict[str, Any]]:
              cur = self._conn.cursor()
        cur.execute(
                      "SELECT event_id, timestamp, event_type, source_region, confidence, content_hash, payload_json FROM events ORDER BY timestamp DESC LIMIT ?",
                      (limit,),
        )
        return [
                      {
                                        "event_id": r[0],
                                        "timestamp": r[1],
                                        "event_type": r[2],
                                        "source_region": r[3],
                                        "confidence": r[4],
                                        "content_hash": r[5],
                                        "payload": json.loads(r[6]),
                      }
                      for r in cur.fetchall()
        ]

    def upsert_rule(self, rule: Dict[str, Any]) -> None:
              cur = self._conn.cursor()
        cur.execute(
                      "INSERT OR REPLACE INTO rules VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (
                                        rule["id"],
                                        rule["name"],
                                        1 if rule.get("enabled", True) else 0,
                                        rule["event_type"],
                                        rule.get("source_region", "*"),
                                        rule["action_type"],
                                        1 if rule.get("require_allowlisted_domain", True) else 0,
                                        rule.get("description", ""),
                      ),
        )
        self._conn.commit()

    def list_rules(self) -> List[Dict[str, Any]]:
              cur = self._conn.cursor()
        cur.execute("SELECT rule_id, name, enabled, event_type, source_region, action_type, require_allowlisted_domain, description FROM rules")
        return [
                      {
                                        "id": r[0],
                                        "name": r[1],
                                        "enabled": bool(r[2]),
                                        "event_type": r[3],
                                        "source_region": r[4],
                                        "action_type": r[5],
                                        "require_allowlisted_domain": bool(r[6]),
                                        "description": r[7],
                      }
                      for r in cur.fetchall()
        ]
