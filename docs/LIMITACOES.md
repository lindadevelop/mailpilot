# Limitações conhecidas (registro honesto)

* A integração com o Outlook **não existe**: o Grok ainda não foi validado a
  fazer leitura/escrita. A Fase 1 importa por JSON, CSV e EML.
* O classificador de pendências é da Fase 2 — nesta fase todas as mensagens
  ficam com estado `Indeterminado`.
* Migrações: o esquema é criado por `create_all` no arranque para o MVP; o
  Alembic está configurado mas sem revisões geradas (primeira revisão a criar
  antes de existir base de dados com dados).
* Sem interface de autenticação de utilizadores: a API usa uma chave única
  (`API_KEY`) e destina-se a correr em `localhost`.
* Sem envio de email, por decisão de âmbito.

## Fase 2 — estado real (10.º registo)

* Classificador implementado: prompt com a conversa COMPLETA, JSON validado,
estados do documento, evidências obrigatórias e correções manuais com precedência.
* `pytest`: **29 testes a passar** (11 da Fase 1 + 18 da Fase 2).
* **Chamada real ao Ollama: NÃO concluída** — o modelo `qwen2.5:7b` e o
  `llama3.2:3b` deram *timeout* aos 120 s nesta máquina (CPU). O erro foi corretamente
  propagado (`OllamaError`) e **nada inválido foi gravado**. Para concluir: aumentar
  o timeout (`OllamaClient(timeout=600)`), manter o modelo carregado (`ollama run`)
  ou usar um modelo mais leve.

## Fase 4 — estado (preferências de comunicação e DISC)

* Implementado: perfil por contacto (formalidade, concisão, detalhe, prazos, pedidos
  explícitos) + **hipótese DISC** (D/I/S/C/combinação/Indeterminado) com confiança e
  citações literais obrigatórias.
* **Limites de uso aplicados no código**: sem citações não há perfil; a hipótese é
  sempre guardada como `sugestao` com aviso de que não é diagnóstico nem serve para
  decisões laborais; uma revisão **confirmada por pessoa** nunca é substituída pela IA;
  o perfil pode ser desativado.
* **Teste real** (llama3.2:3b, contacto cliente@exemplo.pt): hipótese **D**, confiança
  0.8, evidência literal «Bom dia, podem enviar proposta até sexta-feira?». Ressalva de
  qualidade: o modelo classificou como «informal» uma mensagem que começa por «Bom dia»
  e inferiu D a partir de **uma** mensagem — daí o estado ser «sugestão» e não conclusão.
* `pytest`: **48 testes a passar** (39 + 9).

## Acesso pelo túnel (temporário)

O frontend está publicado por um quick tunnel do Cloudflare, apontado ao
`vite preview` (porta do preview) e com `allowedHosts: true` no `vite.config.ts`:

* **https://letting-ide-depends-snapshot.trycloudflare.com** (local: `npm run preview` + `cloudflared tunnel --url http://localhost:5175`)
* O `/api` chega à API local por proxy do próprio Vite, por isso o túnel serve
  frontend **e** dados.
* O URL muda a cada arranque do `cloudflared` — ler de `%TEMP%	unnel-port-5175.log`.

Nota: a API em `:8100` estava a correr com uma versão anterior do código nesta
sessão (os endpoints das Fases 3-5 só aparecem depois de reiniciar o `uvicorn`).
