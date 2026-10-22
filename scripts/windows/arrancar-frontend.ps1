# MailPilot AI — arranca o frontend (http://127.0.0.1:5173)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location "$raiz\frontend"

if (-not (Test-Path 'node_modules')) {
    Write-Host 'A instalar dependências do frontend...'
    npm install
}

npm run dev
