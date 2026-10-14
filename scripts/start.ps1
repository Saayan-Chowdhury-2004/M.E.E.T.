$ErrorActionPreference = "Stop"
Write-Host "[M.E.E.T.] Launching M.E.E.T. in OBSERVE mode with native Windows HUD..."
.\.venv\Scripts\python -m app.main --mode observe --hud
