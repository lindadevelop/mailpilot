# MailPilot AI

Aplicação local de gestão inteligente de email profissional. Mostra o que exige
atenção (quem espera resposta, o que está atrasado, compromissos assumidos) sem
substituir o Outlook.

Documento de referência: `docs/PLANO.md` (plano técnico e fases) e
`docs/LIMITACOES.md` (o que está e não está feito).

## Arranque rápido (Windows)

```powershell
scripts\windows\instalar.ps1      # cria a venv e instala dependências
scripts\windows\arrancar.ps1       # corre a API em http://127.0.0.1:8100
```

Testes:

```powershell
cd backend
..\.venv\Scripts\python -m pytest -q
```

## Arquitetura

* `backend/` — FastAPI + SQLAlchemy (+ Alembic), SQLite no MVP, preparado para PostgreSQL.
* `frontend/` — React + TypeScript (a criar na Fase 1, parte 2).
* `scripts/windows/` — instalação e arranque.
* `docs/` — plano, limitações e notas de integração.

A autenticação da API é feita por chave (`X-API-Key`); a importação de emails
entra por `POST /api/emails/batch` e é **idempotente** por
`(conta, origem, identificador estável)`.

## Frontend (Fase 1, parte 2)

```powershell
scripts\windowsrrancar-frontend.ps1   # http://127.0.0.1:5173
```

O frontend fala com a API por proxy (sem CORS) e guarda a chave `X-API-Key` no
browser, com atualização parcial a cada 30 s.
