$ErrorActionPreference = "Stop"
Write-Host "[M.E.E.T.] Creating Windows Python virtual environment..."
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -e ".[dev,windows]"
Write-Host "[M.E.E.T.] Setup complete."
