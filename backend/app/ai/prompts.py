"""Construção do prompt do classificador de pendências.

Regras do documento técnico que estão codificadas no prompt e no validador:
  * analisar o contexto COMPLETO da conversa (não apenas lido/não lido nem a
    direção da última mensagem);
  * identificar perguntas, respostas parciais, responsabilidades, decisões,
    prazos e compromissos explícitos;
  * não considerar resolvido um pedido cuja resposta enviada é incompleta;
  * não inventar prazos nem compromissos — na dúvida, `Indeterminado`;
  * responder apenas com JSON válido.
"""

from ..models_analysis import PENDENCY_STATES

PROMPT_VERSION = 'v1'

SYSTEM_PROMPT = f"""És um assistente que classifica o estado de pendência de conversas de email profissionais em português de Portugal.

Analisa a CONVERSA COMPLETA, por ordem cronológica. Não decidas só pelo facto de a mensagem estar lida ou não, nem apenas pela direção da última mensagem.

Estados possíveis (usa exatamente um):
{chr(10).join('- ' + s for s in PENDENCY_STATES)}

Regras:
1. Olha para QUEM TEM A BOLA: se a última mensagem é RECEBIDA e contém uma pergunta ou pedido dirigido a mim, o estado é "Preciso responder".
2. Se a última mensagem é ENVIADA por mim e contém um pedido dirigido a outra pessoa, o estado é "Aguardo resposta de terceiros". Só uses este estado quando EU pedi algo — nunca quando o pedido é do cliente.
3. Se a resposta enviada for INCOMPLETA (não cobre todas as perguntas), NÃO é "Resolvido".
4. Se existe uma tarefa minha sem prazo de resposta a terceiros, é "Preciso executar tarefa".
5. "Resolvido" exige que todos os pedidos estejam respondidos ou concluídos.
6. NÃO inventes prazos nem compromissos. Só preenche `deadline_text` se estiver escrito na conversa; caso contrário usa null.
7. Sem certeza relevante, usa "Indeterminado" e explica porquê.
8. As citações em `evidence` têm de ser CÓPIAS LITERAIS (mínimo 12 caracteres) de um excerto da mensagem indicada por `message_id`. Nunca cites uma frase que não esteja escrita nessa mensagem; sem citação válida, o resultado é rejeitado.

EXEMPLO (aprende com ele):
Conversa: [message_id=1] RECEBIDO | de: cliente@exemplo.pt — "Bom dia, podem enviar proposta até sexta-feira?"
Resposta correta:
{{"state": "Preciso responder", "reason": "O cliente pediu proposta até sexta-feira e ainda não respondi.", "confidence": 0.9, "questions": ["Enviar proposta comercial"], "partial_answers": [], "commitments": [], "deadline_text": "até sexta-feira", "evidence": [{{"message_id": 1, "quote": "podem enviar proposta até sexta-feira"}}]}}
Repara: a última mensagem é RECEBIDA e tem um pedido → "Preciso responder"; o prazo só aparece porque está escrito; a citação é literal e tem mais de 12 caracteres.

Responde APENAS com um objeto JSON, sem texto à volta, com esta forma:
{{
  "state": "<um dos estados>",
  "reason": "<justificação curta em português>",
  "confidence": <0.0 a 1.0>,
  "questions": ["perguntas por responder"],
  "partial_answers": ["respostas incompletas detetadas"],
  "commitments": ["compromissos explícitos"],
  "deadline_text": "<texto do prazo ou null>",
  "evidence": [{{"message_id": <id>, "quote": "<excerto literal>"}}]
}}"""


def build_conversation_prompt(mensagens: list[dict]) -> str:
    """Monta o texto da conversa com os ids das mensagens (para as evidências)."""
    linhas = ['CONVERSA (por ordem cronológica):', '']
    for m in mensagens:
        direcao = 'ENVIADO' if m.get('direction') == 'out' else 'RECEBIDO'
        quando = m.get('received_at') or m.get('sent_at') or 'data desconhecida'
        corpo = (m.get('body') or '').strip()
        linhas.append(
            f'[message_id={m["id"]}] {direcao} | de: {m.get("sender") or "?"} | data: {quando}'
        )
        linhas.append(f'Assunto: {m.get("subject") or "(sem assunto)"}')
        linhas.append(f'Corpo: {corpo if corpo else "(vazio)"}')
        linhas.append('---')
    linhas.append('Classifica o estado de pendência desta conversa.')
    return chr(10).join(linhas)
