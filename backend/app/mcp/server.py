"""Servidor MCP (stdio) com as ferramentas do MailPilot.

Transporte: stdio — é o que clientes MCP locais (incluindo o Grok, se suportar MCP)
usam por omissão. Cada ferramenta delega na camada de serviços (`tools.py`), nunca
em SQL direto.

Arranque:
    python -m app.mcp.server

Segurança:
  * o servidor corre em localhost e não abre portas de rede (stdio);
  * a chave/credenciais do cliente MCP ficam fora do MailPilot;
  * nenhuma ferramenta envia, apaga ou move emails — só importa e lê estado.
"""

from __future__ import annotations

import json
from typing import Any

from ..db import SessionLocal, init_db
from . import tools

try:  # SDK v2 (>=2.0): FastMCP foi renomeado para MCPServer
    from mcp.server.mcpserver import MCPServer as _ServidorMCP

    _SDK_VERSAO = 2
except ImportError:  # pragma: no cover
    try:  # SDK v1
        from mcp.server.fastmcp import FastMCP as _ServidorMCP

        _SDK_VERSAO = 1
    except ImportError:
        _ServidorMCP = None  # type: ignore[assignment]
        _SDK_VERSAO = 0


def _com_sessao(fn, *args, **kwargs) -> dict[str, Any]:
    init_db()
    db = SessionLocal()
    try:
        return fn(db, *args, **kwargs)
    finally:
        db.close()


def construir_servidor():
    """Constrói o servidor MCP. Devolve None se o SDK não estiver instalado."""
    if _ServidorMCP is None:  # pragma: no cover
        return None

    servidor = _ServidorMCP('mailpilot')

    @servidor.tool()
    def mailpilot_import_emails(
        account_email: str,
        messages: list[dict[str, Any]],
        source: str = 'grok',
        cursor: str | None = None,
    ) -> str:
        """Importa um lote de mensagens (idempotente por conta/origem/identificador)."""
        return json.dumps(
            _com_sessao(tools.import_emails, account_email, messages, source, cursor), ensure_ascii=False
        )

    @servidor.tool()
    def mailpilot_get_sync_cursor(account_email: str, source: str = 'grok') -> str:
        """Devolve o cursor para retomar a importação."""
        return json.dumps(_com_sessao(tools.get_sync_cursor, account_email, source), ensure_ascii=False)

    @servidor.tool()
    def mailpilot_finish_sync(
        account_email: str,
        source: str = 'grok',
        sync_run_id: int | None = None,
        notes: str | None = None,
    ) -> str:
        """Conclui a sincronização (só depois de os dados estarem persistidos)."""
        return json.dumps(
            _com_sessao(tools.finish_sync, account_email, source, sync_run_id, notes), ensure_ascii=False
        )

    @servidor.tool()
    def mailpilot_get_import_errors(
        limit: int = 20, sync_run_id: int | None = None
    ) -> str:
        """Lista os erros de importação para correção e reenvio."""
        return json.dumps(_com_sessao(tools.get_import_errors, limit, sync_run_id), ensure_ascii=False)

    return servidor


def main() -> None:  # pragma: no cover
    servidor = construir_servidor()
    if servidor is None:
        raise SystemExit(
            'O SDK MCP não está instalado. Instale com: pip install "mcp[cli]".'
        )
    servidor.run()


if __name__ == '__main__':  # pragma: no cover
    main()
