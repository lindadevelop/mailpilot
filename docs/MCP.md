# Servidor MCP — MailPilot AI (Fase 3)

O servidor MCP expõe **quatro ferramentas** que o cliente (Grok) pode chamar. Todas
delegam na mesma camada de serviços da API REST — o MCP nunca escreve SQL.

## Ferramentas

| Ferramenta | Para quê |
|---|---|
| `mailpilot_import_emails` | Importa um lote de mensagens. Idempotente por `(conta, origem, external_id)`: reenviar o mesmo lote não duplica |
| `mailpilot_get_sync_cursor` | Devolve o cursor para o cliente retomar onde parou |
| `mailpilot_finish_sync` | Conclui a sincronização (só depois de os dados estarem persistidos) |
| `mailpilot_get_import_errors` | Lista erros por lote, para o cliente corrigir e reenviar |

## Arranque (transporte stdio)

```bash
cd backend
pip install "mcp[cli]"
python -m app.mcp.server
```

Configuração do cliente MCP (exemplo genérico):

```json
{
  "mcpServers": {
    "mailpilot": {
      "command": "C:/a/mailpilot/.venv/Scripts/python.exe",
      "args": ["-m", "app.mcp.server"],
      "cwd": "C:/a/mailpilot/backend"
    }
  }
}
```

## Regras que o servidor respeita

* **Não envia, não apaga e não move emails** — só importa e lê estado (verificado por teste).
* **Não expõe portas de rede**: o transporte é stdio, local.
* **Payloads inválidos devolvem erro estruturado** (`{"ok": false, "error": ...}`) em vez de rebentar.
* **Erros por item não abortam o lote** e ficam consultáveis por `mailpilot_get_import_errors`.

## Estado real (importante)

* As ferramentas estão implementadas e **testadas** (7 testes), mas o fluxo
  **Outlook → Grok → MCP → MailPilot** continua **NÃO validado**: não houve ainda
  uma chamada real do cliente Grok a este servidor. Só depois desse teste se pode
  declarar a sincronização automática como funcional.
* O SDK `mcp` é opcional: sem ele, `app/mcp/tools.py` continua utilizável e testado
  (é o que a API e os testes usam).

## Nota de compatibilidade (SDK)

O SDK MCP **2.x** renomeou `FastMCP` para `MCPServer`
(`from mcp.server.mcpserver import MCPServer`). O `server.py` suporta as duas
versões: usa `MCPServer` no SDK >= 2 e `FastMCP` no SDK 1.x.

Verificado com o SDK **2.3.0**: servidor construído e as 4 ferramentas registadas
(`mailpilot_import_emails`, `mailpilot_get_sync_cursor`, `mailpilot_finish_sync`,
`mailpilot_get_import_errors`).
