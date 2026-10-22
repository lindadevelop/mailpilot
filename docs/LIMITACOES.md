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
