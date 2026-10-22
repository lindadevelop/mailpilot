# MailPilot AI — plano técnico e fases

## Princípios

1. **Cada fase entrega aplicação executável** — nada de mockups.
2. **Idempotência primeiro**: importar o mesmo lote duas vezes não pode duplicar mensagens.
3. **Conclusão de sincronização só após persistência confirmada**.
4. **Conteúdo de email é entrada não fiável** (resistente a prompt injection) e nunca é escrito nos logs.
5. **Nada de envio, eliminação ou movimentação automática** no MVP.
6. **O Grok é o acesso ao Outlook**, mas nenhuma funcionalidade depende de capacidade não testada: a Fase 1 importa por JSON, CSV e EML.

## Fase 1 — estrutura, base de dados, importação, API e dashboard

* Modelo de dados: contas, contactos, empresas, mensagens, conversas, participantes,
  execuções de sincronização, cursores, erros de importação e auditoria.
* Deduplicação idempotente por `(conta, origem, external_id)` com índice único.
* Importadores JSON, CSV e EML com paginação, retoma por cursor e relatório de progresso.
* API REST com OpenAPI e chave: `/api/emails/batch`, `/api/sync/status`,
  `/api/sync/complete`, `/api/conversations`, `/api/dashboard`.
* Frontend React + TS com página inicial orientada à ação.

## Fase 2 — IA local

Classificador de pendências com contexto da conversa inteira (não apenas o
lido/não lido), com estado, motivo, confiança, evidência e data. Estados:
Preciso responder · Aguardo resposta · Preciso executar tarefa · Acompanhar ·
Em análise · Resolvido · Informativo · Indeterminado.

## Fase 3 — MCP e Grok

Servidor MCP a invocar a mesma camada de serviços do backend (nunca SQL direto):
`mailpilot_import_emails`, `mailpilot_get_sync_cursor`, `mailpilot_finish_sync`,
`mailpilot_get_import_errors`. Só se declara funcional após teste real
Outlook → Grok → MCP → MailPilot.

## Fase 4 — contactos e estilos de comunicação

Preferências observáveis e hipótese DISC com citações e confiança, apresentada
como hipótese de comunicação (nunca diagnóstico nem avaliação de desempenho).

## Fase 5 — sugestões de resposta e relatórios

Rascunhos com revisão humana (objetivo, diplomático, técnico, firme-cordial),
relatório diário e das pendências que mudaram desde a última análise.
