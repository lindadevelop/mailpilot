# MailPilot AI — arranca a API em http://127.0.0.1:8100
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location "$raiz\backend"

& "$raiz\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload
