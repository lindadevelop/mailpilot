# MailPilot AI — instalação no Windows (cria a venv e instala dependências)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $raiz

if (-not (Test-Path '.venv')) {
    Write-Host 'A criar ambiente virtual...'
    python -m venv .venv
}

Write-Host 'A instalar dependências...'
& "$raiz\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$raiz\.venv\Scripts\python.exe" -m pip install -r "$raiz\backend\requirements.txt"

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Criado .env a partir de .env.example — ajuste a API_KEY.'
}

Write-Host 'Concluído. Para arrancar: scripts\windows\arrancar.ps1'
