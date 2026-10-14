"""CLI & Windows Application Entrypoint for M.E.E.T."""
from __future__ import annotations

import argparse
import asyncio

from app.agent import MeetAgent
from app.api import create_api


def main() -> None:
      parser = argparse.ArgumentParser(description="M.E.E.T. — Local Third-Person Meeting Agent")
      parser.add_argument("--host", default="localhost", help="Control API bind host")
      parser.add_argument("--port", type=int, default=8765, help="Control API bind port")
      parser.add_argument("--mode", default="observe", choices=["observe", "suggest", "assist", "autonomous"])
      parser.add_argument("--hud", action="store_true", help="Launch native Windows WebView2 HUD window")
      args = parser.parse_args()

    agent = MeetAgent(config_dir="config", db_path="data/meet_metadata.db")
    agent.mode = args.mode
    agent.hotkey.start()
    _dispatcher = create_api(agent)

    async def observer_loop() -> None:
              while True:
                            res = await agent.step_once()
                            await asyncio.sleep(0.25 if res.get("status") == "active" else 2.0)

          if args.hud:
                    agent.ux.launch_native_hud()
else:
          asyncio.run(observer_loop())


if __name__ == "__main__":
      main()
