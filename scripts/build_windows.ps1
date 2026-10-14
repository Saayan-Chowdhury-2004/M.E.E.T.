$ErrorActionPreference = "Stop"
Write-Host "[M.E.E.T.] Packaging standalone Windows executable via PyInstaller..."
.\.venv\Scripts\python -m pip install pyinstaller
.\.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name "MEET-Agent" `
  --add-data "config;config" `
    --add-data "frontend;frontend" `
      app/main.py
      Write-Host "[M.E.E.T.] Build complete: dist\MEET-Agent.exe"
